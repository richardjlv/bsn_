"""BSN-P03 adaptation: marked update while patient status is already critical.
This does not measure a distinct emergency-detection event.
"""
import threading
import time

import pytest
import rospy
from pytest_bdd import scenarios, given, when, then
from messages.msg import SensorData, TargetSystemData
from temporal_capture import monotonic_ns

scenarios("./features/BSN-P03.feature")
SENSORS = ("thermometer", "ecg", "oximeter", "abps", "abpd", "glucosemeter")
RISK_FIELDS = ("trm_risk", "ecg_risk", "oxi_risk", "abps_risk", "abpd_risk", "glc_risk")


def reading(sensor, risk, value):
    msg = SensorData()
    msg.type, msg.risk, msg.data, msg.batt = sensor, risk, value, 100.0
    return msg


@pytest.fixture
def hub_probe():
    if not rospy.core.is_initialized():
        rospy.init_node("bdd_bsn_p03", anonymous=True)
    state = {"lock": threading.Lock(), "outputs": [], "stop": threading.Event(),
             "load": None, "sent": [], "current": reading("thermometer", 90.0, 41.625)}

    def receive(msg):
        stamp = monotonic_ns()
        with state["lock"]:
            state["outputs"].append((stamp, msg))

    state["subscriber"] = rospy.Subscriber("/TargetSystemData", TargetSystemData, receive, queue_size=200)
    state["publishers"] = {s: rospy.Publisher("/" + s + "_data", SensorData, queue_size=100)
                           for s in SENSORS}
    try:
        deadline = time.time() + 15.0
        while time.time() < deadline:
            if all(p.get_num_connections() for p in state["publishers"].values()):
                break
            time.sleep(0.05)
        assert all(p.get_num_connections() for p in state["publishers"].values()), "Hub inputs not connected"
        time.sleep(5.0)
        yield state
    finally:
        state["stop"].set()
        if state["load"] is not None:
            state["load"].join(timeout=2.0)
        state["subscriber"].unregister()
        for pub in state["publishers"].values():
            pub.unregister()


def critical_baseline(msg):
    return (msg.trm_risk == 90.0 and msg.trm_data == 41.625
            and all(getattr(msg, key) == 10.0 for key in RISK_FIELDS[1:])
            and 60.0 < msg.patient_status <= 100.0)


@given("the patient has three consecutive confirmed critical status outputs")
def established_high_risk(hub_probe):
    start = monotonic_ns()
    for sensor, pub in hub_probe["publishers"].items():
        msg = hub_probe["current"] if sensor == "thermometer" else reading(sensor, 10.0, 36.5)
        pub.publish(msg)
    deadline = time.time() + 15.0
    while time.time() < deadline:
        with hub_probe["lock"]:
            outputs = [msg for stamp, msg in hub_probe["outputs"] if stamp >= start]
        if len(outputs) >= 3 and all(critical_baseline(msg) for msg in outputs[-3:]):
            print("BSN-P03 precondition: three critical outputs; patient_status={}".format(
                outputs[-1].patient_status))
            return
        time.sleep(0.01)
    raise AssertionError("Patient critical state not established before timing")


@given("high-risk thermometer traffic is maintained at 20 Hz for two seconds")
def load(hub_probe):
    def stream():
        while not hub_probe["stop"].is_set():
            with hub_probe["lock"]:
                hub_probe["publishers"]["thermometer"].publish(hub_probe["current"])
                hub_probe["sent"].append(monotonic_ns())
            hub_probe["stop"].wait(0.05)
    hub_probe["load"] = threading.Thread(target=stream)
    hub_probe["load"].daemon = True
    hub_probe["load"].start()
    time.sleep(2.0)
    with hub_probe["lock"]:
        stamps = list(hub_probe["sent"])
    rate = (len(stamps) - 1) * 1e9 / (stamps[-1] - stamps[0]) if len(stamps) > 1 else 0
    assert 18.0 <= rate <= 22.0, "Load precondition failed: {} Hz".format(rate)


@when("a new marked high-risk thermometer update is published")
def high_risk(hub_probe):
    msg = reading("thermometer", 90.0, 42.125)
    with hub_probe["lock"]:
        assert hub_probe["outputs"], "No patient state before stimulus"
        baseline_stamp, baseline = hub_probe["outputs"][-1]
        assert critical_baseline(baseline), "Patient is not critical immediately before stimulus"
        assert monotonic_ns() - baseline_stamp <= 1000000000, "Patient baseline older than 1s"
        hub_probe["current"] = msg
        hub_probe["start"] = monotonic_ns()
        hub_probe["publishers"]["thermometer"].publish(msg)


@then("the new marker and a critical patient status are received within 250 ms")
def emergency(hub_probe):
    start = hub_probe["start"]
    deadline = start + 2000000000
    matched = None
    while monotonic_ns() < deadline:
        with hub_probe["lock"]:
            outputs = list(hub_probe["outputs"])
        matches = [(stamp, msg) for stamp, msg in outputs if stamp >= start
                   and msg.trm_risk == 90.0 and msg.trm_data == 42.125
                   and 60.0 < msg.patient_status <= 100.0]
        if matches:
            matched = matches[0]
            break
        time.sleep(0.001)
    assert matched is not None, "No matching critical patient status within 2s; observed={}".format(
        [(round((stamp-start)/1e6, 3), msg.trm_risk, msg.patient_status)
         for stamp, msg in outputs if stamp >= start])
    elapsed_ms = (matched[0] - start) / 1e6
    print("BSN-P03: risk=90, patient_status={}, latency_ms={:.3f}".format(
        matched[1].patient_status, elapsed_ms))
    assert elapsed_ms <= 250.0, "BSN-P03: marked update with established critical status took {:.3f} ms (limit 250 ms)".format(elapsed_ms)

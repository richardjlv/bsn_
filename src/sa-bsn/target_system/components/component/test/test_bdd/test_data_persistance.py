import threading
import time
import uuid
from archlib.msg import Status, Persist
import ros_pytest
import pytest
from pytest_bdd import given, when, then, parsers, scenario
from test_sensor import SharedSensorTests
import rospy
import rosnode
from asserts import is_node_receiving_multiple_topics, node_is_active, is_node_publishing_to_topics,check_time_performance
from parsers import process_real_time_topics, parse_topic_data, capture_topic_data

FEATURE_FILE = "./features/data_persistance.feature"

PERSISTENCE_NODES = [
    "/g4t1",
    "/collector",
    "/param_adapter",
    "/g3t1_3",
    "/data_access",
    "/logger"
]

# Individual @scenario per test (not bulk scenarios()) so @pytest.mark.xfail can attach to a collected item;
# same style as bsn_ros2's test_data_persistance.py and test_injector.py.

@scenario(FEATURE_FILE, "A marked sensor status reaches the persistence channel (BSN-P08 observation)")
def test_sensor_status_forwarded_to_persistence_channel():
    pass


PERSISTENCE_FAILURE_GAP_REASON = (
    "gap, not a regression: DataAccess.cpp has no storage-failure branch (no 'PersistenceFailure' type). "
    "rosnode.kill_nodes('/logger') never kills the node mid-scenario, and the old 'fail' check passed only via "
    "/g4t1's unrelated 'fail' Status. See bsn_ros2's features/DATA_PERSISTANCE_GAPS.md"
)


@pytest.mark.xfail(reason=PERSISTENCE_FAILURE_GAP_REASON)
@scenario(FEATURE_FILE, "A persistence failure is recorded when the knowledge repository cannot store a reading (BSN-P08)")
def test_persistence_failure_recorded():
    pass


def node_is_online():
    node_is_active(PERSISTENCE_NODES)

def step_then_system_logs_failure(context):
    """Ensure the system logs a persistence failure identifying the reading that failed (what the Gherkin asks for).
    Expected to fail today: nothing in this codebase publishes a 'PersistenceFailure' type."""
    persist_topic = parse_topic_data('/persist')
    failure_sources = {
        source for source, record_type in zip(persist_topic.get('source', ()), persist_topic.get('type', ()))
        if record_type == 'PersistenceFailure'
    }
    assert failure_sources, (
        "No PersistenceFailure record was logged while the knowledge "
        "repository was experiencing storage failures: {0}".format(persist_topic)
    )
    assert context['sensor'] in failure_sources, (
        "PersistenceFailure record(s) were logged ({0}) but none identified "
        "the thermometer reading actually reported ({1})".format(failure_sources, context['sensor'])
    )

@given('the knowledge repository is experiencing storage failures')
def step_given_knowledge_repository_storage_failures(context):
    """Arm the persistence system so the upcoming reading fails to be stored."""
    node_is_online()
    context['simulate_persistence_failure'] = True


@pytest.fixture
def persistence_probe():
    if not rospy.core.is_initialized():
        rospy.init_node('bdd_persistence', anonymous=True)
    probe = {'records': [], 'lock': threading.Lock()}

    def receive(msg):
        with probe['lock']:
            probe['records'].append(msg)

    sub = rospy.Subscriber('/persist', Persist, receive, queue_size=100)
    pub = rospy.Publisher('/log_status', Status, queue_size=10)
    probe['publisher'] = pub
    try:
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if pub.get_num_connections() and sub.get_num_connections():
                break
            time.sleep(0.05)
        assert pub.get_num_connections(), 'Logger status input not connected'
        assert sub.get_num_connections(), 'Persistence output not connected'
        yield probe
    finally:
        pub.unregister()
        sub.unregister()


@given('the logger persistence channel is ready for a controlled sensor status')
def persistence_ready(persistence_probe):
    pass


@when('a uniquely marked thermometer status is sent to the logger')
def send_marked_status(persistence_probe):
    msg = Status()
    msg.source = '/g3t1_3'
    msg.target = '/bdd06/' + uuid.uuid4().hex
    msg.content = 'success'
    persistence_probe['expected'] = msg
    persistence_probe['publisher'].publish(msg)


def matches_status(record, expected):
    return (record.type == 'Status' and record.source == expected.source
            and record.target == expected.target and record.content == expected.content)


@then('a corresponding Status record with the same source target and content reaches persist')
def status_reaches_persist(persistence_probe):
    expected = persistence_probe['expected']
    deadline = time.time() + 10.0
    while time.time() < deadline:
        with persistence_probe['lock']:
            records = list(persistence_probe['records'])
        if any(matches_status(record, expected) for record in records):
            return
        time.sleep(0.01)
    raise AssertionError('No matching Status on /persist for source={} target={}; records={}'.format(
        expected.source, expected.target,
        [(r.type, r.source, r.target, r.content) for r in records]))


@then('a persistence failure record identifying that reading should be available in the system log')
def step_then_persistence_failure_record_available(context):
    step_then_system_logs_failure(context)

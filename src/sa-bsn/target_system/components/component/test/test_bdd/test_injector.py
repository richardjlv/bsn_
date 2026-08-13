import ros_pytest
from pytest_bdd import scenarios, given, when, then, parsers
from conftest import check_topic_inbound_from_node
from interface_map import SYSTEM_MAP

scenarios("./features/injector.feature")

@then(parsers.parse('{node} should publish "{topic}" to <sensor>'))
def then_inject_uncertainty_to_sensor(context, node, topic, sensor):
    topic_name = SYSTEM_MAP[topic] + SYSTEM_MAP[sensor]
    check_topic_inbound_from_node(context, topic_name, SYSTEM_MAP[node])

@then(parsers.parse('{node} should publish "{topic}" to the system log'))
def then_inject_uncertainty(context, node, topic):
    check_topic_inbound_from_node(context, SYSTEM_MAP[topic], SYSTEM_MAP[node])
import pytest
import rospy
import rostopic
import ros_pytest
from std_msgs.msg import String, Float64
from asserts import is_node_publishing_to_topics, Command, TIMEOUT_SECONDS
from parsers import get_rostopic_sensor_data, get_rosnode_info
from messages.msg import SensorData
from archlib.msg import Uncertainty, Status
import subprocess
import threading
from services.srv import PatientData, PatientDataResponse, PatientDataRequest
import rosnode
import rosservice
import time

SENSORS = ['/g3t1_1', '/g3t1_2', '/g3t1_3', '/g3t1_4', '/g3t1_5', '/g3t1_6']
low_risk_value_dict = {
    'oxigenation': 90.0,
    'heart_rate': 90.0,
    'temperature': 37.0,
    'abps': 100.0,
    'abpd': 70.0,
    'glucose': 90.0
}
high_risk_value_dict = {
    'oxigenation': 50.0,
    'heart_rate': 120.0,
    'temperature': 45.0,
    'abps': 250.0,
    'abpd': 95.0,
    'glucose': 200.0
}
mid_risk_value_dict = {
    'oxigenation': 60,
    'heart_rate': 100.0,
    'temperature': 40.0,
    'abps': 130.0,
    'abpd': 85.0,
    'glucose': 100.0
}
out_of_range_value_dict = {
    'oxigenation': 101,
    'heart_rate': 301,
    'temperature': 51.0,
    'abps': 301.0,
    'abpd': 305.0,
    'glucose': 301.0
}
low_risk_threshold_dict = 20
high_risk_threshold_dict = 66

class SharedSensorTests:
    """Shared test methods for sensor testing"""

    @staticmethod
    def assert_sensors_are_publishing_data(node, topic_name):
        """Assert that sensors are actively publishing data"""
        is_publishing, missing_topics = is_node_publishing_to_topics(node, topic_name)
        assert is_publishing, "{} is missing data from these topics: {}".format(node, missing_topics)
    
    @staticmethod
    def assert_topic_has_data(sensor_topic_name, timeout=5.0):
        """Assert that a topic is publishing data within a timeout period"""
        try:
            sensor_data = {}
            cmd = ['rostopic', 'echo', sensor_topic_name, '-n', '1']
            topic_executor = Command(cmd)
            stdout_bytes, stderr_bytes, returncode = topic_executor.run(timeout=TIMEOUT_SECONDS)
            sensor_data[sensor_topic_name] = get_rostopic_sensor_data(returncode, stdout_bytes, stderr_bytes)
            assert sensor_data[sensor_topic_name]['data'], "No data published on topic {}".format(sensor_topic_name)
        except Exception as e:
            if str(e) == "TimeoutExpired":
                raise AssertionError("Timeout: No data published on topic {}".format(sensor_topic_name))
            else:
                raise

    @pytest.fixture(autouse=True)
    def sensor_environment(self, request):
        if not rospy.core.is_initialized():
            rospy.init_node('node_test', anonymous=True)
        self.message_lock = threading.Lock()
        self.received_messages = []
        self.service_calls = 0
        values = low_risk_value_dict
        for fixture, candidate in (
                ('mock_high_risk_service', high_risk_value_dict),
                ('mock_mid_risk_service', mid_risk_value_dict),
                ('mock_out_of_range_service', out_of_range_value_dict)):
            if fixture in request.fixturenames:
                values = candidate

        def respond(req):
            with self.message_lock:
                self.service_calls += 1
            response = PatientDataResponse()
            response.data = values[req.vitalSign]
            return response

        self.patient_service_server = rospy.Service('getPatientData', PatientData, respond)
        self.subscriber = rospy.Subscriber(self.topic, SensorData, self.message_callback)
        try:
            deadline = time.time() + 10.0
            while time.time() < deadline:
                with self.message_lock:
                    if self.service_calls >= 2:
                        break
                rospy.sleep(0.05)
            assert self.service_calls >= 2, 'Sensor did not call the patient mock twice within 10s'
            with self.message_lock:
                self.received_messages[:] = []
            yield
        finally:
            self.subscriber.unregister()
            if self.patient_service_server is not None:
                self.patient_service_server.shutdown('Test complete')
                self.patient_service_server = None

    @staticmethod
    def mock_patient_data_service_callback(req):
        """
        Funcao callback que simula a logica do servidor.
        Recebe a requisicao (PatientData) e retorna uma Resposta de Low Risk (PatientDataResponse).
        """
        rospy.loginfo("Servico 'getPatientData' chamado no teste: {}".format(req.vitalSign))
        
        res = PatientDataResponse()
        res.data = low_risk_value_dict[req.vitalSign]
        return res

    def message_callback(self, msg):
        """Callback for receiving messages from the sensor"""
        print("Mensagem recebida no topico {}: data={}".format(self.topic, msg.data))
        with self.message_lock:
            self.received_messages.append(msg)
    
    def wait_for_message(self, timeout=5.0, matcher=None):
        """Wait for a message to be received"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.message_lock:
                for message in reversed(self.received_messages):
                    if matcher is None or matcher(message):
                        return message
            time.sleep(0.01)
        return None

    def wait_for_status(self, status_messages, status_lock, timeout=2.0, matcher=None):
        """Wait for a status message to be received"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with status_lock:
                if status_messages:
                    if matcher is None:
                        return status_messages[-1]
                    for msg in status_messages:
                        if matcher(msg):
                            return msg
            time.sleep(0.01)
        return None

    def test_transfer_with_low_risk_data(self):
        """Test transfer with low risk data"""
        test_data = low_risk_value_dict[self.vital_sign]
        received_msg = self.wait_for_message(matcher=lambda msg: msg.data == test_data)
        assert received_msg is not None
        assert received_msg.risk < low_risk_threshold_dict
        assert received_msg.data == test_data

    @pytest.fixture
    def mock_high_risk_service(self):
        pass

    def test_transfer_with_high_risk_data(self, mock_high_risk_service):
        """Test transfer with high risk  data"""
        test_data = high_risk_value_dict[self.vital_sign]
        received_msg = self.wait_for_message(matcher=lambda msg: msg.data == test_data)

        assert received_msg is not None
        assert received_msg.risk > high_risk_threshold_dict
        assert received_msg.data == test_data

    @pytest.fixture
    def mock_mid_risk_service(self):
        pass

    def test_transfer_with_mid_risk_data(self, mock_mid_risk_service):
        """Test transfer with mid risk  data"""
        test_data = mid_risk_value_dict[self.vital_sign]
        received_msg = self.wait_for_message(matcher=lambda msg: msg.data == test_data)
        assert received_msg is not None
        assert received_msg.risk > low_risk_threshold_dict and received_msg.risk < high_risk_threshold_dict
        assert received_msg.data == test_data

    @pytest.fixture
    def mock_out_of_range_service(self):
        pass

    def test_transfer_with_out_of_range_data(self, mock_out_of_range_service):
        """Test transfer with out of range data"""
        calls_before = self.service_calls
        received_msg = self.wait_for_message()
        assert received_msg is None
        assert self.service_calls > calls_before, "Sensor stopped requesting out-of-range input"
        assert "/" + self.node_name in rosnode.get_node_names(), "Sensor exited during the observation"

    def test_transfer_with_accuracy_fail(self, mock_mid_risk_service):
        """Test transfer with accuracy fail (label mismatch)"""
        status_messages = []
        status_lock = threading.Lock()

        def status_callback(msg):
            with status_lock:
                status_messages.append(msg)

        status_subscriber = rospy.Subscriber(
            "collect_status",
            Status,
            status_callback
        )

        received_msg = self.wait_for_message()
        assert received_msg is not None

        uncertainty_topics = [
            "uncertainty_{}".format(self.node_name),
            "uncertainty_/{}".format(self.node_name),
        ]
        uncertainty_pubs = [
            rospy.Publisher(topic, Uncertainty, queue_size=10)
            for topic in uncertainty_topics
        ]
        time.sleep(0.2)

        uncertainty_msg = Uncertainty()
        uncertainty_msg.source = "test"
        uncertainty_msg.target = self.node_name
        uncertainty_msg.content = "noise_factor=0.3"

        for _ in range(3):
            for publisher in uncertainty_pubs:
                publisher.publish(uncertainty_msg)
            time.sleep(0.2)

        status_msg = self.wait_for_status(
            status_messages,
            status_lock,
            timeout=6.0,
            matcher=lambda msg: msg.source.endswith(self.node_name) and msg.content == "fail"
        )
        status_subscriber.unregister()

        assert status_msg is not None
        assert status_msg.source.endswith(self.node_name)
        assert status_msg.content == "fail"

        
    def test_battery_consumption(self, mock_mid_risk_service):
        """Test that battery level decreases after operations"""
        received_msg1 = self.wait_for_message()
        assert received_msg1 is not None
        initial_battery = received_msg1.batt
        
        # Wait for next message
        time.sleep(0.5)
        with self.message_lock:
            del self.received_messages[:]
        received_msg2 = self.wait_for_message()
        
        assert received_msg2 is not None, "No second sample for battery comparison"
        assert received_msg2.batt <= initial_battery

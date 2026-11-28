from test_sensor_connected import ConnectedSensorTestMixin


class TestG3T1_4ConnectedSensor(ConnectedSensorTestMixin):
    __test__ = True
    # These sensors use PatientData even with connect_sensor=true.
    uses_patient_service = True
    topic = "abps_data"
    connected_service_name = "abps"
    expected_vital_sign = "abps"
    expect_connected_value = True
    expect_unknown_label_in_connected = True
    node_name = "node_test_g3t1_4_connected"

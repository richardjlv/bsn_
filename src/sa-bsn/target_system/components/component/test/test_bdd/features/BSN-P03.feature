Feature: BSN-P03 adapted observation with patient already in critical state
  # Critical means patient_status > 60. Inputs are synthetic SensorData.
  # Measures marked-update publication to TargetSystemData receipt, not a distinct emergency event.
  # Under load, the new marker identifies a stream phase, not an individual repeated packet.

  @timing @bsn-p03
  Scenario: A new high-risk update is reported within 250 ms while the patient is already critical
    Given the patient has three consecutive confirmed critical status outputs
    When a new marked high-risk thermometer update is published
    Then the new marker and a critical patient status are received within 250 ms

  @timing @sad-path @bsn-p03
  Scenario: A new high-risk update is reported within 250 ms under 20 Hz traffic while already critical
    Given the patient has three consecutive confirmed critical status outputs
    And high-risk thermometer traffic is maintained at 20 Hz for two seconds
    When a new marked high-risk thermometer update is published
    Then the new marker and a critical patient status are received within 250 ms

Feature: Persistence channel observations related to BSN-P08
  # BDD06 checks forwarding only, not storage or retrieval of vital-sign values.

  @behavior @bsn-p08 @persistence
  Scenario: A marked sensor status reaches the persistence channel (BSN-P08 observation)
    Given the logger persistence channel is ready for a controlled sensor status
    When a uniquely marked thermometer status is sent to the logger
    Then a corresponding Status record with the same source target and content reaches persist

	@behavior @sad-path @bsn-p08 @persistence @gap
	# xfail (ver PERSISTENCE_FAILURE_GAP_REASON): o DataAccess.cpp nunca teve branch de falha de armazenamento, entao nao ha
	# caminho "errado" a corrigir. O antigo `'fail' in content` passava por ruido do /g4t1 e porque o kill do /logger nunca
	# funciona.
	Scenario: A persistence failure is recorded when the knowledge repository cannot store a reading (BSN-P08)
		Given the knowledge repository is experiencing storage failures
		When the thermometer reports a new vital sign reading
		Then a persistence failure record identifying that reading should be available in the system log

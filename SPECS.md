# SA-BSN: estrutura de build e testes

O workspace usa ROS Melodic, Catkin e C++11. Os testes ROS Python usam
Python 2.7, pytest e pytest-bdd por meio de ros_pytest. A instalação e os
comandos de execução estão no [README.md](README.md#ros-1-test-environment-melodic--python-27).

## Testes ativos

- Componentes: `src/sa-bsn/target_system/components/component/test/unit/`.
- Steps BDD: `src/sa-bsn/target_system/components/component/test/test_bdd/`.
- Gherkin: `src/sa-bsn/target_system/components/component/test/test_bdd/features/`.
- Fixtures BDD compartilhadas: `src/sa-bsn/target_system/components/component/test/conftest.py`.
- Outras suítes ROS: `test/unit/` de data_access, logger, enactor e param_adapter.
- Testes C++ de bibliotecas: `src/libbsn/test/` e `src/archlib/test/`.

Os registros ficam no CMakeLists.txt de cada pacote. Cada rostest executa
uma suite completa com seu proprio master ROS, compartilhado pelos casos.
BDD17 e BDD18 usam launches separados; os demais cenarios do managing system
compartilham um launch. Nao e necessario iniciar a aplicacao externamente.

Os testes de sensores possuem seu próprio mock de getPatientData. As faixas
e demais parâmetros continuam em `test/patient_parameters.launch`, sem
iniciar o paciente real. O executável patient_data_service continua ativo
nos testes de integração. BDD20 verifica a continuidade dos comandos no sistema integrado.
A suíte behave, os experimentos C++ sem registro e o exemplo pybind11 foram
retirados do ambiente de testes.

## Cobertura e resultados

O pacote component habilita instrumentação LLVM quando os testes são
compilados com Clang (`-fprofile-instr-generate -fcoverage-mapping`), não GCOV.
O fluxo está em `coverage.sh`; `COVERAGE_SCOPE.md` descreve seu alcance e suas
limitações. Os resultados XML e logs devem usar um novo diretório a cada
campanha, preservando as execuções anteriores.

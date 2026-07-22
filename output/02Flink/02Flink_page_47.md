## 第47页

67 # other TaskManagers. If not specified, the TaskManager will try different strategies to identify

68 # the address.

76 taskmanager.host: node01

89 # The number of task slots that each TaskManager offers. Each slot runs one parallel pipeline.

91 taskmanager.numberOfTaskSlots: 2

93 # The parallelism used for programs that did not specify and other parallelism.

$$
95 parallelism.default: 2
$$

188 # The address to which the REST client will connect to

190 rest.address: node01

200 # To enable this, set the bind address to one that has access to outside-facing

201 # network interface, such as 0.0.0.0.

202 #

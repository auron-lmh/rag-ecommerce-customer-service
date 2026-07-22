## 第69页

EnvironmentSettings settings = EnvironmentSettings.inStreamingMode();

TableEnvironment tableEnv = TableEnvironment.create(settings);

$$
String name = "myhive";
$$

$$
String defaultDatabase = "mydatabase";
$$

$$
String hiveConfDir = "/opt/hive-conf";
$$

$$
HiveCatalog hive = new HiveCatalog(name, defaultDatabase, hiveConfDir);
$$

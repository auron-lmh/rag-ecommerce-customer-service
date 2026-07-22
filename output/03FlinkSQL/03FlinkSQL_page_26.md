## 第26页

// isVirtual 是表示： 当这个表被sink表时，该字段是否出现在schema中

.columnByMetadata("offs",DataTypes.BIGINT(),"offset", true) // 声明元数据字段

.columnByMetadata("ts",DataTypes.TIMESTAMP_LTZ(3),"timestamp",true) // 声明元数据字段

$$
/\*.primaryKey("id","name")*/
$$

$$
.build()
$$

$$
.format("json")
$$

$$
.option("topic","mytopic")
$$

$$
.option("properties.bootstrap.servers","hdp01:9092")
$$

$$
.option("properties.group.id","g1")
$$

$$
.option("scan.startup.mode","earliest-offset")
$$

$$
.option("json.fail-on-missing-field","false")
$$

$$
.option("json.ignore-parse-errors","true")
$$

$$
.build()
$$

$$
)
$$

tenv.executeSql("select * from t_person").print();

- • SQL代码

tenv.executeSql(

"create table t_person

$$
"
$$

$$
+
$$

$$
(
$$

$$
"
$$

$$
+
$$

$$
id int,
$$

$$
"
$$

$$
+
$$

$$
// 物理字段
$$

$$
"
$$

$$
+
$$

$$
"
$$

## 第6页

- catalog_name.database_name.object_name

- 用户可以指定一个 catalog 和数据库作为 “当前catalog” 和“当前数据库”。

- 如果前两部分的标识符没有指定，那么会使用当前的 catalog 和当前数据库。

- 用户也可以通过 Table API 或 SQL 切换当前的 catalog 和当前的数据库。

TableEnvironment tEnv = ...;

tEnv.useCatalog("custom_catalog");

tEnv.useDatabase("custom_database");

Table table = ...;

// register the view named 'exampleView' in the catalog named

'custom_catalog'

// in the database named 'custom_database'

tableEnv.createTemporaryView("exampleView", table);

// register the view named 'exampleView' in the catalog named

'custom_catalog'

// in the database named 'other_database'

// register the view named 'example.view' in the catalog named

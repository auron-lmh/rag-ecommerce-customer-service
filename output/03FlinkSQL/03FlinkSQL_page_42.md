## 第42页

## 8.1.3. CUBE

- . CUBE is a shorthand notation for specifying a common type of grouping set.

- . It represents the given list and all of its possible subsets - the power set.

SELECT supplier_id, rating, product_id, COUNT(*)

FROM (VALUES

('supplier1', 'product1', 4),

('supplier1', 'product2', 3),

('supplier2', 'product3', 3),

('supplier2', 'product4', 4))

AS Products(supplier_id, product_id, rating)

GROUP BY CUBE (supplier_id, rating, product_id)

SELECT supplier_id, rating, product_id, COUNT(*)

FROM (VALUES

('supplier1', 'product1', 4),

('supplier1', 'product2', 3),

('supplier2', 'product3', 3),

('supplier2', 'product4', 4))

AS Products(supplier_id, product_id, rating)

GROUP BY GROUPING SET (

(supplier_id, product_id, rating),

(supplier_id, product_id),

(supplier_id, rating),

(supplier_id),

(product_id, rating),

(product_id),

(rating),

()

)

## 8.2. 开窗聚合

- • 在标准 SQL 中还有另外一类比较特殊的聚合方式，可以针对每一行计算一个聚合值。

- • 比如说，我们可以以每一行数据为基准，计算它之前 1 小时内所有数据的平均值；也可以计算它之前 10 个数的平均值。

- • 就好像是在每一行上打开了一扇窗户、收集数据进行统计一样，这就是所谓的“开窗函数”。

- • 开窗函数的聚合与之前两种聚合有本质的不同：

- ○ 分组聚合、窗口 TVF 聚合都是“多对一”的关系，将数据分组之后每组只会得到一个聚合结果；

23 rows in set

省2

<NULL>

<NULL>

省2

312

市2

省2

209

市2

县2

108

省3

省3

省3

省3

省3

省3

省3

省3

省3

省3

省3

省3

省3

省3

省3

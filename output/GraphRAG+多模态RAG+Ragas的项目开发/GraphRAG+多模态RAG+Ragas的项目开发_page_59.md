## 第57页

The position of each point represents the relative relationship of words in the semantic space, with coordinate values indicating

Points that are closer together signify higher semantic similarity. The dashed lines indicate concepts that are closely related.

上图展示了密集向量在二维空间中的表现形式。虽然实际应用中的密集向量通常具有更高的维度，但

上述代码片段中的 dim 参数表示向量字段中要保存的向量嵌入的维数。 FLOAT_VECTOR 值表示向

量字段持有 32 位浮点数列表，通常用于表示反比例。除此之外，还支持以下类型的向量嵌入：

FLOAT16_VECTOR

这种类型的向量场保存一个 16 位半精度浮点数列表，通常适用于内存或带宽受限的深度学习或基

于 GPU 的计算场景。

BFLOAT16_VECTOR

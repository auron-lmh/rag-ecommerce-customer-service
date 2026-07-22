## 第84页

64位明文

IP

第一轮

第二轮

第十六轮

32位互换

IP-1

DES 使用一个 56 位的密钥以及附加的 8 位奇偶校验位，产生最大 64 位的分组大小。这是一个迭代的分组密码，使用称为 Feistel 的技术，其中将加密的文本块分成两半。使用子密钥对其中一半应用循环功能，然后将输出与另一半进行“异或”运算；接着交换这两半，这一过程会继续下去，但最后一个循环不交换。DES 使用 16 个循环，使用异或，置换，代换，移位操作四种基本运算。

DES 的常见变体是三重 DES，使用 168 位的密钥对资料进行三次加密的一种机制；它通常（但非始终）提供极其强大的安全性。如果三个 56 位的子元素都相同，则三重 DES 向后兼容 DES。

攻击 DES 的主要形式被称为蛮力的或彻底密钥搜索，即重复尝试各种密钥直到有一个符合为止。

如果 DES 使用 56 位的密钥，则可能的密钥数量是 2 的 56 次方个。随着计算机系统能力的不断发展，DES 的安全性比它刚出现时会弱得多，然而从非关键性质的实际出发，仍可以认为它是足够的。不过，DES 仅用于旧系统的鉴定，而更多地选择新的加密标准 — 高级加密标准（Advanced Encryption Standard，AES）。

新的分析方法有差分分析法和线性分析法两种

15.1.4. 代码实现

import javax.crypto.Cipher;

import javax.crypto.SecretKeyFactory;

import javax.crypto.spec.DESKeySpec;

import javax.crypto.spec.IvParameterSpec;

import java.security.Key;

import java.util.Base64;

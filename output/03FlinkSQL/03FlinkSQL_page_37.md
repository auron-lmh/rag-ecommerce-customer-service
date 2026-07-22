## 第37页

## 7.3. CUMULATE

- Cumulating windows【累积窗口】在某些场景中非常有用。

- 例如每日仪表板从00:00到每分钟绘制累积UV数，10:00的UV线代表从00:00到10:00的UV总数，这可以通过累积窗口轻松有效地实现

- CUMULATE函数将元素分配给覆盖在初始步长间隔内的行，并将每一步扩展为多一个步长(保持window start固定)，直到最大窗口大小。

- 可以把cumulative函数看作应用TUMBLE窗口，首先使用最大窗口大小，然后将每个滚动窗口分割成几个具有相同窗口开始和窗口结束步长差异的窗口。

- 因此，累积窗口确实是重叠的，而且没有固定的大小。

- CUMULATE 函数有三个必需的参数:

$$
CUMULATE(TABLE data, DESCRIPTOR(timecol), step, size)
$$

- data: 表参数，此表需要包含有一个时间属性列【time attribute column】

- timecol: 一个列描述符，指示数据的哪个时间属性列应该映射到滑动的窗口

案例:

window slide

window size

user 1

user 2

window 1

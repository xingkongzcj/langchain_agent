# Java 学习核心知识笔记

## 一、Java 语言概述

Java 是由 Sun Microsystems 公司（后被 Oracle 收购）于 1995 年推出的面向对象编程语言。
Java 之父是詹姆斯·高斯林（James Gosling），最初设计目标是为消费类电子产品提供可移植的编程语言。

Java 的核心设计理念是"一次编写，到处运行"（Write Once, Run Anywhere）。
实现这一目标的关键是 Java 虚拟机（JVM）：Java 源代码先编译成字节码（.class 文件），
再由不同平台上的 JVM 解释执行，从而实现跨平台。

Java 的主要应用领域：
1. 企业级后端开发（Spring Boot、微服务）
2. 大数据处理（Hadoop、Spark、Flink）
3. 安卓移动开发
4. 金融、电商等高并发系统

Java 目前主流的长期支持版本是 Java 8、Java 11、Java 17 和 Java 21。

## 二、Java 基础语法

Java 是强类型语言，变量必须先声明类型再使用。

八大基本数据类型：
- 整数型：byte（1字节）、short（2字节）、int（4字节）、long（8字节）
- 浮点型：float（4字节）、double（8字节）
- 字符型：char（2字节，Unicode）
- 布尔型：boolean（1位）

基本数据类型与引用类型的区别：
- 基本类型直接存储值，存放在栈上
- 引用类型存储对象的地址，对象存放在堆上

自动装箱与拆箱：
- 装箱：基本类型自动转换为包装类（int → Integer）
- 拆箱：包装类自动转换为基本类型（Integer → int）
- 注意：Integer 缓存 -128 到 127，超出范围用 == 比较会返回 false

## 三、面向对象三大特性

### 封装

封装是指把对象的属性和方法隐藏在类内部，只对外暴露必要的接口。
实现方式：将属性用 private 修饰，提供 public 的 getter 和 setter 方法。
好处：保护数据安全，防止外部随意修改内部状态。

### 继承

继承是指子类复用父类的属性和方法，使用 extends 关键字实现。
Java 只支持单继承（一个子类只能有一个直接父类），但支持多层继承。
子类可以重写（Override）父类的方法，方法名、参数列表、返回类型必须一致。

关键字 super 用于在子类中调用父类的构造方法或方法。
所有类默认继承自 Object 类，Object 提供了 equals、hashCode、toString 等方法。

### 多态

多态是指同一个方法在不同对象上表现出不同的行为。
实现前提：
1. 有继承关系
2. 子类重写父类方法
3. 父类引用指向子类对象

示例：
Animal animal = new Dog();
animal.speak();  // 调用的是 Dog 的 speak 方法

多态的好处是提高代码的扩展性和可维护性，实现面向接口编程。

## 四、Java 集合框架

Java 集合框架主要分为两大接口：Collection 和 Map。

### List 接口

- ArrayList：底层是数组，查询快、增删慢，线程不安全
- LinkedList：底层是双向链表，增删快、查询慢
- Vector：线程安全，但性能差，已不推荐使用

### Set 接口

- HashSet：基于哈希表，元素无序、不可重复
- LinkedHashSet：保留插入顺序
- TreeSet：基于红黑树，元素自动排序

### Map 接口

- HashMap：基于哈希表 + 链表 + 红黑树（Java 8 后），键不可重复
- LinkedHashMap：保留插入顺序
- TreeMap：按 key 自动排序
- ConcurrentHashMap：线程安全的 HashMap，性能优于 Hashtable

HashMap 的底层原理：
- 数组 + 链表 + 红黑树
- 默认初始容量 16，负载因子 0.75
- 当链表长度超过 8 且数组长度 ≥ 64 时，链表转为红黑树

## 五、异常处理

Java 异常体系的根类是 Throwable，分为两大类：

1. Error：系统级错误，程序无法处理（如 OutOfMemoryError）
2. Exception：程序可以处理的异常

Exception 又分为：
- 受检异常（Checked）：编译时必须处理（如 IOException）
- 非受检异常（Unchecked）：运行时异常，继承自 RuntimeException（如 NullPointerException）

异常处理语法：
```java
try {
    // 可能抛出异常的代码
} catch (SpecificException e) {
    // 处理具体异常
} catch (Exception e) {
    // 兜底处理
} finally {
    // 无论是否异常都执行（用于释放资源）
}
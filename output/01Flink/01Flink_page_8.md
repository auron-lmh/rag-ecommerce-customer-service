## 第8页

<dependency>
  <groupId>org.apache.flink</groupId>
  <artifactId>flink-statebackend-rocksdb</artifactId>
  <version>${flink.version}</version>
</dependency>

<!-- 日志系统 -->
<dependency>
  <groupId>org.apache.logging.log4j</groupId>
  <artifactId>log4j-slf4j-impl</artifactId>
  <version>${log4j.version}</version>
  <scope>runtime</scope>
</dependency>

<dependency>
  <groupId>org.apache.logging.log4j</groupId>
  <artifactId>log4j-api</artifactId>
  <version>${log4j.version}</version>
  <scope>runtime</scope>
</dependency>

<dependency>
  <groupId>org.apache.logging.log4j</groupId>
  <artifactId>log4j-core</artifactId>
  <version>${log4j.version}</version>
  <scope>runtime</scope>
</dependency>
</dependencies>

## 2.3.2. Log4j 配置

http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software

# distributed under the License is distributed on an "AS IS" BASIS,

# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

# See the License for the specific language governing permissions and

# Limitations under the License.

rootLogger.level = WARN

rootLogger.appenderRef.console.ref = ConsoleAppender

appender.console.name = ConsoleAppender

appender.console.type = CONSOLE

appender.console.layout.type = PatternLayout

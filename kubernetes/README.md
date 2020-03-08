# Docker学习

## 安装
```shell
wget -qO- https://get.docker.com/ | sh
sudo usermod -aG docker yczhang
docker --version
```

## 镜像

docker image pull是下载镜像的命令。镜像从远程镜像仓库服务的仓库中下载。

默认情况下，镜像会从 Docker Hub 的仓库中拉取。

docker image pull alpine:latest命令会从 Docker Hub 的 alpine 仓库中拉取标签为 latest 的镜像。

docker image ls列出了本地 Docker 主机上存储的镜像。可以通过 --digests 参数来查看镜像的 SHA256 签名。

docker image inspect命令非常有用！该命令完美展示了镜像的细节，包括镜像层数据和元数据。

docker image rm用于删除镜像。

docker image rm alpine:latest命令的含义是删除 alpine:latest 镜像。当镜像存在关联的容器，并且容器处于运行（Up）或者停止（Exited）状态时，不允许删除该镜像。

## 容器

1) docker container run
启动新容器的命令。该命令的最简形式接收镜像和命令作为参数。镜像用于创建容器，而命令则是希望容器运行的应用。

docker container run -it ubuntu /bin/bash 命令会在前台启动一个 Ubuntu 容器，并运行 Bash Shell。

Ctrl-PQ 会断开 Shell 和容器终端之间的链接，并在退出后保持容器在后台处于运行（UP）状态。
2) docker container ls
用于列出所有在运行（UP）状态的容器。如果使用 -a 标记，还可以看到处于停止（Exited）状态的容器。
3) docker container exec
用于在运行状态的容器中，启动一个新进程。该命令在将 Docker 主机 Shell 连接到一个运行中容器终端时非常有用。

docker container exec -it <container-name or container-id> bash 命令会在容器内部启动一个 Bash Shell 进程，并连接到该 Shell。

为了使该命令生效，用于创建容器的镜像必须包含 Bash Shell。
4) docker container stop
此命令会停止运行中的容器，并将状态置为 Exited(0)。

该命令通过发送 SIGTERM 信号给容器内 PID 为 1 的进程达到目的。

如果进程没有在 10s 之内得到清理并停止运行，那么会接着发送 SIGKILL 信号来强制停止该容器。

docker container stop 可以接收容器 ID 以及容器名称作为参数。
5) docker container start
重启处于停止（Exited）状态的容器。可以在 docker container start 命令中指定容器的名称或者 ID。
6) docker container rm
删除停止运行的容器。可以通过容器名称或者 ID 来指定要删除的容器。推荐首先使用 docker container stop 命令停止容器，然后使用 docker container rm 来完成删除。
7) docker container inspect
显示容器的配置细节和运行时信息。该命令接收容器名称和容器 ID 作为主要参数。

## Docker应用容器化

### 基本步骤
完整的应用容器化过程主要分为以下几个步骤。
1. 编写应用代码。
2. 创建一个 Dockerfile，其中包括当前应用的描述、依赖以及该如何运行这个应用。
3. 对该 Dockerfile 执行 docker image build 命令。
4. 等待 Docker 将应用程序构建到 Docker 镜像中。

```Dockerfile
FROM alpine
LABEL maintainer="nigelpoulton@hotmail.com"
RUN apk add --update nodejs nodejs-npm
COPY . /src
WORKDIR /src
RUN npm install
EXPOSE 8080
ENTRYPOINT ["node", "./app.js"]
```
### 最佳实践

常见的例子是，每一个 RUN 指令会新增一个镜像层。因此，通过使用 && 连接多个命令以及使用反斜杠（\）换行的方法，将多个命令包含在一个 RUN 指令中，通常来说是一种值得提倡的方式。

另一个问题是开发者通常不会在构建完成后进行清理。当使用 RUN 执行一个命令时，可能会拉取一些构建工具，这些工具会留在镜像中移交至生产环境。

有多种方式来改善这一问题——比如常见的是采用建造者模式（Builder Pattern）。但无论采用哪种方式，通常都需要额外的培训，并且会增加构建的复杂度。

建造者模式需要至少两个 Dockerfile，一个用于开发环境，一个用于生产环境。

首先需要编写 Dockerfile.dev，它基于一个大型基础镜像（Base Image），拉取所需的构建工具，并构建应用。

接下来，需要基于 Dockerfile.dev 构建一个镜像，并用这个镜像创建一个容器。

这时再编写 Dockerfile.prod，它基于一个较小的基础镜像开始构建，并从刚才创建的容器中将应用程序相关的部分复制过来。

整个过程需要编写额外的脚本才能串联起来。

这种方式是可行的，但是比较复杂。

多阶段构建（Multi-Stage Build）是一种更好的方式！

多阶段构建能够在不增加复杂性的情况下优化构建过程。

下面介绍一下多阶段构建方式。

多阶段构建方式使用一个 Dockerfile，其中包含多个 FROM 指令。每一个 FROM 指令都是一个新的构建阶段（Build Stage），并且可以方便地复制之前阶段的构件。

```Dockerfile
FROM node:latest AS storefront
WORKDIR /usr/src/atsea/app/react-app
COPY react-app .
RUN npm install
RUN npm run build

FROM maven:latest AS appserver
WORKDIR /usr/src/atsea
COPY pom.xml .
RUN mvn -B -f pom.xml -s /usr/share/maven/ref/settings-docker.xml dependency
\:resolve
COPY . .
RUN mvn -B -s /usr/share/maven/ref/settings-docker.xml package -DskipTests

FROM java:8-jdk-alpine AS production
RUN adduser -Dh /home/gordon gordon
WORKDIR /static
COPY --from=storefront /usr/src/atsea/app/react-app/build/ .
WORKDIR /app
COPY --from=appserver /usr/src/atsea/target/AtSea-0.0.1-SNAPSHOT.jar .
ENTRYPOINT ["java", "-jar", "/app/AtSea-0.0.1-SNAPSHOT.jar"]
CMD ["--spring.profiles.active=postgres"]
```

首先注意到，Dockerfile 中有 3 个 FROM 指令。每一个 FROM 指令构成一个单独的构建阶段。

各个阶段在内部从 0 开始编号。不过，示例中针对每个阶段都定义了便于理解的名字。
1. 阶段 0 叫作 storefront。
2. 阶段 1 叫作 appserver。
3. 阶段 2 叫作 production。

storefront 阶段拉取了大小超过 600MB 的 node:latest 镜像，然后设置了工作目录，复制一些应用代码进去，然后使用 2 个 RUN 指令来执行 npm 操作。

这会生成 3 个镜像层并显著增加镜像大小。指令执行结束后会得到一个比原镜像大得多的镜像，其中包含许多构建工具和少量应用程序代码。

appserver 阶段拉取了大小超过 700MB 的 maven:latest 镜像。然后通过 2 个 COPY 指令和 2 个 RUN 指令生成了 4 个镜像层。

这个阶段同样会构建出一个非常大的包含许多构建工具和非常少量应用程序代码的镜像。

production 阶段拉取 java:8-jdk-alpine 镜像，这个镜像大约 150MB，明显小于前两个构建阶段用到的 node 和 maven 镜像。

这个阶段会创建一个用户，设置工作目录，从 storefront 阶段生成的镜像中复制一些应用代码过来。

之后，设置一个不同的工作目录，然后从 appserver 阶段生成的镜像中复制应用相关的代码。最后，production 设置当前应用程序为容器启动时的主程序。

重点在于 COPY --from 指令，它从之前的阶段构建的镜像中仅复制生产环境相关的应用代码，而不会复制生产环境不需要的构件。

还有一点也很重要，多阶段构建这种方式仅用到了一个 Dockerfile，并且 docker image build 命令不需要增加额外参数。

使用 no-install-recommends
在构建 Linux 镜像时，若使用的是 APT 包管理器，则应该在执行 apt-get install 命令时增加 no-install-recommends 参数。

这能够确保 APT 仅安装核心依赖（Depends 中定义）包，而不是推荐和建议的包。这样能够显著减少不必要包的下载数量。

不要安装 MSI 包（Windows）

## Docker Compose

Docker Compose 与 Docker Stack 非常类似。它能够在 Docker 节点上，以单引擎模式（Single-Engine Mode）进行多容器应用的部署和管理。

```shell
pip3 install docker-compose
```

Docker Compose 使用 YAML 文件来定义多服务的应用。YAML 是 JSON 的一个子集，因此也可以使用 JSON。

Docker Compose 默认使用文件名 docker-compose.yml。当然，也可以使用 -f 参数指定具体文件。

如下是一个简单的 Compose 文件的示例，它定义了一个包含两个服务（web-fe 和 redis）的小型 Flask 应用。

这是一个能够对访问者进行计数并将其保存到 Redis 的简单的 Web 服务。


```yml
version: "3.5"
services:
web-fe:
build: .
command: python app.py
ports:
- target: 5000
published: 5000
networks:
- counter-net
volumes:
- type: volume
source: counter-vol
target: /code
redis:
image: "redis:alpine"
networks:
counter-net:

networks:
counter-net:

volumes:
counter-vol:
```

1) docker-compose up
用于部署一个 Compose 应用。

默认情况下该命令会读取名为 docker-compose.yml 或 docker-compose.yaml 的文件。

当然用户也可以使用 -f 指定其他文件名。通常情况下，会使用 -d 参数令应用在后台启动。
2) docker-compose stop
停止 Compose 应用相关的所有容器，但不会删除它们。

被停止的应用可以很容易地通过 docker-compose restart 命令重新启动。
3) docker-compose rm
用于删除已停止的 Compose 应用。

它会删除容器和网络，但是不会删除卷和镜像。
4) docker-compose restart
重启已停止的 Compose 应用。

如果用户在停止该应用后对其进行了变更，那么变更的内容不会反映在重启后的应用中，这时需要重新部署应用使变更生效。
5) docker-compose ps
用于列出 Compose 应用中的各个容器。

输出内容包括当前状态、容器运行的命令以及网络端口。
6) docker-compose down
停止并删除运行中的 Compose 应用。

它会删除容器和网络，但是不会删除卷和镜像。

## 卷
1) docker volume create
命令用于创建新卷。默认情况下，新卷创建使用 local 驱动，但是可以通过 -d 参数来指定不同的驱动。
2) docker volume ls
会列出本地 Docker 主机上的全部卷。
3) docker volume inspect
用于查看卷的详细信息。可以使用该命令查看卷在 Docker 主机文件系统中的具体位置。
4) docker volume prune
会删除未被容器或者服务副本使用的全部卷。
5) docker volume rm
删除未被使用的指定卷。

# Ubuntu物理节点上部署Kubernets集群




## 准备条件

1. 所有节点上已经安装docker版本1.2+和用来控制Linux网桥的bridge-utils
   shell脚本安装docker:
   ```shell
   $ apt-get update
   $ apt install bridge-utils
   $ curl -fsSL https://get.docker.com -o get-docker.sh
   $ sudo sh get-docker.sh
   $ sudo usermod -aG docker your-user
   ```
2. 所有的机器可相互通信。主节点需要连接到Interent去下载必须的文件
3. 所有的服务器能够使用ssh远程密钥认证登入，而不是用密码登入
   ```shell
   $ apt-get update
   $ apt-get install openssh-server
   $ service ssh start
   $ gedit /etc/ssh/sshd_config
   ```
   把配置文件中的"PermitRootLogin without-password"注释掉,并配置PermitRootLogin yes
4. 配置免密登录
   ```shell
   $ ssh-keygen
   $ ssh-copy-id -i /home/yczhang/.ssh/id_rsa.pub root@10.10.10.126
   ```

## 安装Kubernets

1. 添加源并安装
    ```shell
    $ deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
    $ apt-get update && apt-get install -y apt-transport-https
    $ curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | apt-key add -
    $ apt-get update && apt-get install -y kubelet kubeadm kubectl
    ```
2. 初始化主节点
   ```shell
   $ swapoff -a
   $ kubeadm init --apiserver-advertise-address=10.10.10.175 --image-repository registry.aliyuncs.com/google_containers --pod-network-cidr=192.168.0.0/16 –fail-swap-on=false –ignore-preflight-errors=Swap
   ```

   ```shell
   $ kubeadm join 10.10.10.175:6443 --token hzru1f.68n260ix3l4navto \
    --discovery-token-ca-cert-hash sha256:ec55bc4398f3be1b2b20f290aa01f69dadb11c92d530a4d507b017284981fc42
   ```

   初始化遇到问题的清理命令
   ```shell
   $ kubeadm reset
   $ ifconfig cni0 down
   $ ip link delete cni0
   $ ifconfig flannel.1 down
   $ ip link delete flannel.1
   $ rm -rf /var/lib/cni/
   ```

3. 其他节点加入集群
   ```shell
   $ kubeadm join 10.10.10.175:6443 --token hzru1f.68n260ix3l4navto \
    --discovery-token-ca-cert-hash sha256:ec55bc4398f3be1b2b20f290aa01f69dadb11c92d530a4d507b017284981fc42
   ```

4. 配置环境参数
   ```shell
   $ echo "export KUBECONFIG=/etc/kubernetes/admin.conf" >> ~/.bash_profile
   $ source ~/.bash_profile
   ```
## 相关命令

### 查看已加入的节点
kubectl get nodes
### 查看集群状态
kubectl get cs

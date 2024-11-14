# Introduction
This file describes `demo` example for Base Docker Image. Example contains `Docker file` which overrides Base Docker Image,
Robot Framework file (*.robot) with keywords and test cases, special python files to exclude some tags (see documentation),
`docker-compose.yml` file.

# Configuration
`tests_holder.robot` file contains Robot Framework test cases. You can add new test cases or keywords to test `PlatformLibrary`.
To configure `docker-compose.yml` file you should configure Kubernetes configuration file (set environment, context, etc.),
mount you host folder which contains "./kube/config" file (or custom kubeconfig), specify `KUBECONFIG` environment variable
with path to mounted kubeconfig file. For example, you have the following kubeconfig file: C:/Users/test/.kube/config,
you can mount disk "C" to "/mnt" directory in `volumes` block of docker-compose.yml (- C:/:/mnt) and specify `KUBECONFIG` 
environment variable as /mnt/Users/test/.kube/config:
```yaml
version: '2'
services:
  integration-tests:
    build:
      context: ./
      dockerfile: docker/Dockerfile
    ports:
      - 8090:8080
    volumes:
      - ./docker/robot/tests:/opt/robot/tests
      - ./output:/opt/robot/output
      - C:/:/mnt
    environment:
      - KUBECONFIG=/mnt/Users/test/.kube/config
      - DEBUG=true
    command: ["run-robot"]
```

# Execution
Navigate to `demo` folder and execute:
```bash
docker-compose up -d --build
```
`output` folder will be generated in `demo` folder with Robot Framework results.   
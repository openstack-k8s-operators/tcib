# tcib

TCIB stands for the container image build.
It is a repository to build OpenStack services container images.

## Building containers

1. Generate repos using repo-setup tool
```
$ git clone https://github.com/openstack-k8s-operators/repo-setup
$ cd repo-setup
$ python setup.py install --user
$ # Make a directory to store the generated repos
$ mkdir /tmp/repos
$ # Generate repos using repo-setup tool
$ repo-setup current-podified -b zed -o /tmp/repos
```

2. Install ansible-core and Buildah tool
```
$ sudo dnf -y install ansible-core buildah
```

3. Install the tcib tool
```
$ git clone https://github.com/openstack-k8s-operators/tcib
$ cd tcib
$ sudo pip install -r requirements.txt
$ sudo python setup.py install
$ sudo openstack tcib container image build --help
```

4. Build keystone container using tcib
```
$ # create containers.yaml file
$ cat containers.yaml
container_images:
  - imagename: quay.io/podified-main-centos9/openstack-base:current-podified
  - imagename: quay.io/podified-main-centos9/openstack-keystone:current-podified
$ sudo openstack tcib container image build --config-file containers.yaml --repo-dir /tmp/repos/
```

## License

* Free software: Apache license

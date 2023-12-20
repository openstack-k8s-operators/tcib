# tcib

TCIB stands for The Container Image Build.
It is a repository to build OpenStack services container images.

## Setup

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

3. Define subset of images to build

By default all images and their dependencies will be built as specified
in `container-images/containers.yaml` This can be limited to a subset of images
and their depedencies with a custom containers file:

```
$ cat containers.yaml
container_images:
  - imagename: quay.io/podified-master-centos9/openstack-keystone:current-podified
```

## Building images from installed tcib

When tcib is installed from pip or a package, container templates are installed
in `/usr/share/tcib/container-images/tcib` which will render to buildah scripts and Dockerfile files when images are built with:

```
$ sudo openstack tcib container image build --config-file containers.yaml --repo-dir /tmp/repos/
```

## Building images with local changes

When doing local development, images can be built from modifications in the
local directory:

```
# setup for local development
$ git clone https://github.com/openstack-k8s-operators/tcib
$ cd tcib
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt -e ./
$ source tcib-dev-env.rc

# make local development changes, then build images
$ openstack tcib container image build --config-file containers.yaml --repo-dir /tmp/repos/ --tcib-extras tcib_package=
```

The `--tcib-extras tcib_package=` is required so that non-template files are sourced from the local `container-images/kolla` instead of from the `python-tcib-containers` package in the container build.

## Matching container images to tcib commits

1. Look at the container image in quay.io
   (e.g. https://quay.io/repository/podified-antelope-centos9/openstack-tempest-extras?tab=tags)
   and take the tag you want to translate to tcib commit.
2. The tag is the commit hash in https://trunk.rdoproject.org/centos9-antelope/current-podified/
   (e.g. https://trunk.rdoproject.org/centos9-antelope/current-podified/8f/cc/8fcc848d6c766b48142f0ffef9e34937/)
3. Look into the `delorean.repo` file and search for `delorean-component-podified`, the file will point to the
   tcib repo hash
   (e.g. https://trunk.rdoproject.org/centos9-antelope/component/podified/7b/f4/7bf4dba1708c55fa9b3a0c929f18084c85bfe3d6_dbfdef11)

You can also map the quay.io tag to a set of jobs that did the build via
`https://trunk.rdoproject.org/api-centos9-antelope/api/civotes_agg_detail.html?ref_hash=<quay.io tag>`

## License

* Free software: Apache license

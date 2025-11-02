To build:
    cd src
    podman build --platform linux/amd64 -t dashboard-authz-example:v1.0 -f Containerfile

To push to quay.io:
    podman push dashboard-authz-example:v1.0 quay.io/jzeng/dashboard-authz-example:v1.0

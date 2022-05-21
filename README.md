# gandynamic

A dirty script to push a DNS record pointing to your dynamic IPv4 IP, using Gandi's LiveDNS service.

Usable as a K8s job.

This is based on [this script](https://virtuallytd.com/post/dynamic-dns-using-gandi/), with some refinements.

A full rewrite to a proper language is planned.

## K8s cronjonb example

### Push your Gandi API key in a K8s secret

```shell
kubectl create secret generic gandynamic --from-literal="API_KEY=<YOUR_GANDI_APIKEY>"
```

### Cronjob manifest

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: gandynamic
spec:
  schedule: "*/10 * * * *"
  jobTemplate:
    spec:
      ttlSecondsAfterFinished: 600
      template:
        spec:
          containers:
          - name: gandynamic
            image: ghcr.io/dekonnection/gandynamic:latest
            imagePullPolicy: IfNotPresent
            envFrom:
              - configMapRef:
                  name: gandynamic
            env:
              - name: API_KEY
                valueFrom:
                  secretKeyRef:
                    name: gandynamic
                    key: API_KEY
          restartPolicy: OnFailure
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: gandynamic
data:
  DOMAIN: <your_domain>
  SUBDOMAIN: <your_dns_record>
```

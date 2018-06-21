# rancher-lbu

Rancher load balancer update

write for gitlab CI as a service

required
```bash
RANCHER_URL=http://rancher.my
RANCHER_ACCESS_KEY=
RANCHER_SECRET_KEY=
RANCHER_PROJECT_ID=1a5
RANCHER_LB_ID=1s36 # load balancer
ENV_DOMAIN=rancher.dev.my # end of domain
```
from gitlab CI (auto)
```bash
CI_PROJECT_PATH_SLUG=smarttv  
CI_ENVIRONMENT_SLUG=cies
```

install in gitlab ci
```yaml
review:
  image:
    name: rancher/cli:v0.6.9
    entrypoint: ["/bin/sh", "-c"]
  service:    
  - name: negash/rancher-lbu
    alias: rlbu
  script:
    - cd .rancher
    - rancher up --stack $CI_PROJECT_PATH_SLUG --force-upgrade --confirm-upgrade --pull --interval "5000" --batch-size 1
    - export SERVICE_ID=`rancher ps | grep $CI_PROJECT_PATH_SLUG/service-name-for-LB | awk '{print $1}'`
    - wget rlbu/$SERVICE_ID -O-
    - apk add --no-cache curl # ping my service (LB is update)
    - echo Update Load balancer; for i in $(seq 1 20); do if [[ "$(curl --connect-timeout 30 -o /dev/null -s -w '%{http_code}\n' http://$CI_PROJECT_PATH_SLUG-$CI_ENVIRONMENT_SLUG.$ENV_DOMAIN)" != "200" ]]; then echo wait 200ok;sleep 1; fi done
  environment:
    name: review/$CI_ENVIRONMENT_SLUG
    on_stop: stop_review
```


```bash
curl 
```
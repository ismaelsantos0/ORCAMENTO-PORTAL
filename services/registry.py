from services.cftv_install import plugin as cftv_install
from services.fence import plugin as fence
from services.concertina_linear import plugin as concertina_linear

SERVICE_REGISTRY = {
    cftv_install.id: cftv_install,
    fence.id: fence,
    concertina_linear.id: concertina_linear,
}

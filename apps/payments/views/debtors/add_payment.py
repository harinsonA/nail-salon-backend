from bootstrap_modal_forms.generic import BSModalUpdateView

from apps.common.views.base_views import ProtectedView
from apps.payments.views.debtors.common import PaymentInstallmentMixin

"""========================================================================="""
# region ........ Views


class AddPaymentModalView(PaymentInstallmentMixin, ProtectedView, BSModalUpdateView):
    pass


# endregion
"""========================================================================="""

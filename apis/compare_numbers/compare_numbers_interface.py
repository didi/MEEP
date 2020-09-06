from apis.compare_numbers.compare_numbers_provider import CompareNumbersProvider
from apis.base import BaseInterface
from apis.utils import load_parameter, route, completes_dialog


class CompareNumbersInterface(BaseInterface):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.provider = CompareNumbersProvider()

    # bind an HTTP endpoint to this function
    @route('/compare_numbers/compare', methods=['POST'])
    def compare(self, request_params):
        number1 = load_parameter(request_params, "number1")
        number2 = load_parameter(request_params, "number2")
        return self.api_call(self.provider.compare,
                             request_params, number1, number2)

    @route('/end_dialog', methods=['POST'])
    @completes_dialog(success=True, confirmation_type='rate_satisfaction')
    def end_dialog(self, request_params):
        return self.api_call(self.provider.end_dialog, request_params)

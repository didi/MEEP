class CompareNumbersProvider():
    def compare(self, num1, num2):
        try:
            num1 = float(num1)
            num2 = float(num2)
        except ValueError:
            raise ValueError('numbers must be parsable by python `float`')

        if num1 == num2:
            result = "equal to"
        elif num1 > num2:
            result = "greater than"
        else:
            result = "less than"
        return [{'name': 'comparison', 'value': result}]

    def end_dialog(self):
        return []

    def __repr__(self) -> str:
        '''Return an executable initialization for this class for executable logs'''
        return 'CompareNumbersProvider()'

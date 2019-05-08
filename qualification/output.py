def pass_check(check):
    print('\033[92m' + '[ ✓ ] ' + check + '\033[0m')

def fail_check(check):
    print('\033[91m' + '[ ✗ ] ' + check + '\033[0m')
    print('Qualification Failed. Resolve Issue & Try Again.')
    exit()

def warn_check(check):
    print('\033[93m' + '[WARNING] ' + check + '\033[0m')

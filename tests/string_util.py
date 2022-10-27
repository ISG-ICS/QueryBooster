class StringUtil:
    
    # Trim all whitespaces inside a multiple line string
    #
    @staticmethod
    def strim(x: str) -> str:
        return ' '.join([line.strip() for line in x.splitlines()]).strip()


if __name__ == '__main__':
    input = '''
            SELECT e1.name, e1.age, e2.salary
            FROM employee AS e1,
                employee AS e2
            WHERE e1.<x1> = e2.<x1>
            AND e1.age > 17
            AND e2.salary > 35000
        '''
    print(StringUtil.strim(input))
class StringUtil:
    
    # Trim all whitespaces inside a multiple line string
    #
    @staticmethod
    def strim(x: str) -> str:
        return ' '.join([' '.join(line.split()) for line in x.splitlines()]).strip()


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

    input = '''
            SELECT     COUNT(<x1>.admin_permission_id) AS col_0_0_
            FROM       <x1>
            INNER JOIN blc_admin_role_permission_xref AS allroles1_
            ON         <x1>.admin_permission_id = allroles1_.admin_permission_id
            INNER JOIN blc_admin_role AS adminrolei2_
            ON         allroles1_.admin_role_id = adminrolei2_.admin_role_id
            WHERE      <x1>.is_friendly = 1
            AND        adminrolei2_.admin_role_id = 1
    '''
    print(StringUtil.strim(input))

    input = '''
        SELECT <x3> 
        FROM   <x1> 
        WHERE  <x6> IN (
            SELECT <x5> 
            FROM   <x2> 
            WHERE  <x4> = <x8>
        )
    '''
    print(StringUtil.strim(input))
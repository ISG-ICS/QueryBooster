import * as React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import 'github-markdown-css/github-markdown.css';

// Static readme content (in Markdown)
const readmeContent = `
# QueryBooster

[**https://github.com/ISG-ICS/QueryBooster**](https://github.com/ISG-ICS/QueryBooster)

QueryBooster is a middleware-based **query rewriting** framework.

![Architecture](framework.png)

QueryBooster intercepts SQL queries by customizing JDBC drivers used by applications (e.g., Tableau) and uses rules to rewrite the queries to semantically equivalent yet more efficient queries. The rewriting rules are designed by data experts who analyze slow queries and apply their domain knowledge and optimization expertise. QueryBooster can accelerate queries formulated by Tableau up to 100 times faster.

## Start to use **QueryBooster**

1. Sign in through the top-right \`SIGN IN WITH GOOGLE\` button.

![Sign in with Google](sign-in-with-google.png)

2. Create an **Application** from the \`Applications\` page. (Take down the \`GUID\` value of your application.)

![Create an application](create-an-application.png)

3. Download the *customized* JDBC Driver using the \`DOWNLOAD\` button from the \`JDBC Drivers\` page, and put it in your application's required directory.

![Download JDBC Driver](download-jdbc-driver.png)

4. Download the **config file** for your JDBC Driver using the \`CONFIG FILE\` button from the \`JDBC Drivers\` page, and put it in your home directory.

![Download Config File](download-config-file.png)

5. Modify the **config file** by input \`your application's GUID\`.

![Modify Config File](modify-config-file.png)

Now, you can start using **QueryBooster** to 

## Browse \`Query Logs\` for your application

![Browse Query Logs](browse-query-logs.png)

## Add \`Rewriting Rules\` to accelerate your queries

![Rewriting Rules](rewriting-rules.png)

#### Either using the \`VarSQL\` Rule Language

![Add a Rewriting Rule](add-a-rewriting-rule.png)

#### Or provding examples to the \`Rule Formulator\` to automatically generate rules

![Formulate a rule using examples](formulate-a-rule-using-examples.png)

## \`VarSQL\` Rule Language

The syntax of VarSQL to define a rewriting rule is as follows:

\`\`\`
[Rule] ::= [Pattern] / [Constraints] --> [Replacement] / [Actions].
\`\`\`

 - The “Pattern” and “Replacement” components define how a query is matched and rewritten into a new query. 
 - The “Constraints” component defines additional conditions that cannot be specified by a pattern such as
schema-dependent conditions. 
 - The “Actions” component defines extra operations that the replacement cannot express, such as replacing a table’s references with another table’s.


The main idea of using VarSQL to define a rule’s pattern is to extend the SQL language with variables. 
A variable in a SQL query pattern can represent an existing SQL element such as a table, a column, a value, an expression, a predicate, a sub-query, etc. 
In this way, a user can formulate a query pattern as easily as writing a normal SQL query. 
The only difference is that, using VarSQL, one can use a variable to represent a specific SQL element so that the pattern can match a broad set of SQL queries. 
The pattern and replacement in a VarSQL rule have to be a full or partial SQL query optionally variablized.
The variables and their matching conditions are defined in the following Table.

![VarSQL Variables Definitions](varlsql-variables-definitions.png)

`;

const ReadMe = () => {
  return (
    <div className="markdown-container">
      <div className="markdown-body">
        <ReactMarkdown rehypePlugins={[rehypeRaw]}>{readmeContent}</ReactMarkdown>
      </div>
    </div>
  );
};

export default ReadMe;
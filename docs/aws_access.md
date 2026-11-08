# Acesso AWS para a conta pessoal e para toda a POC

## Escolha de identidade

**Conta pessoal avulsa:** use um usuário IAM humano `medallion-poc-operator` com acesso ao console, MFA e `aws login --profile medallion-poc`. A AWS CLI v2 instalada neste projeto (2.39.6) oferece credenciais temporárias para esse fluxo; o boto3 com o extra AWS CRT também reconhece o perfil. Não é necessário criar uma role IAM separada. Não crie access keys permanentes para este caminho.

**Conta que já usa AWS Organizations com IAM Identity Center:** peça um permission set dedicado à POC e atribua-o ao seu usuário/grupo. O Identity Center cria e mantém a role IAM correspondente; configure `aws configure sso --profile medallion-poc` e `aws sso login --profile medallion-poc`. Não crie a role manualmente.

Não habilite AWS Organizations apenas para esta POC sem conferir o plano da conta: a [AWS informa](https://docs.aws.amazon.com/singlesignon/latest/userguide/enable-identity-center.html) que, em uma conta Free Tier, criar uma organização pode migrá-la para um plano pago e encerrar créditos Free Tier. A instância de conta isolada do Identity Center não oferece permission sets para acesso à conta AWS.

## Antes do console

1. Escolha `us-east-1` para os dados da POC (ou uma região única, alterando scripts/políticas). IAM é global.
2. Anote o ID de 12 dígitos da conta no menu superior direito do console. Defina o bucket como `medallion-it-tickets-poc-<ID_DA_CONTA>-us-east-1`.
3. Nos dois modelos de política em `config/`, substitua **todas** as ocorrências de `123456789012` pelo ID real. Se usar outro nome de bucket ou região, substitua todas as ocorrências correspondentes. O nome do banco futuro fica fixado em `medallion_it_tickets_poc` e o workgroup Athena em `primary`. Os arquivos terminam em `.template.json` justamente para impedir o uso acidental dos ARNs de exemplo.
4. Verifique se a conta já tem um administrador IAM ou uma identidade de console com permissão para criar usuários/políticas. Se somente root existir, use root apenas para criar a identidade inicial, com MFA ativado, e depois saia dessa sessão. O script de provisionamento recusa root.

Para gerar cópias prontas para colar no console, use o ID anotado no passo 2:

```bash
export POC_ACCOUNT_ID='SEU_ID_DE_12_DIGITOS'
mkdir -p data/staging
sed "s/123456789012/$POC_ACCOUNT_ID/g" config/iam_poc_runtime_policy.template.json > data/staging/iam_poc_runtime_policy.json
sed "s/123456789012/$POC_ACCOUNT_ID/g" config/iam_poc_bootstrap_policy.template.json > data/staging/iam_poc_bootstrap_policy.json
python3 -m json.tool data/staging/iam_poc_runtime_policy.json >/dev/null
python3 -m json.tool data/staging/iam_poc_bootstrap_policy.json >/dev/null
```

Substitua `SEU_ID_DE_12_DIGITOS` pelo ID real. Os arquivos gerados ficam em `data/staging/`, ignorado pelo Git. Confira visualmente os ARNs antes de criar as políticas.

## Conta pessoal avulsa: passo a passo no console

### A. Criar as duas políticas do projeto

No [console IAM](https://console.aws.amazon.com/iam/), abra **Policies > Create policy > JSON**.

1. Cole o conteúdo gerado em `data/staging/iam_poc_runtime_policy.json`. Escolha **Next**, corrija alertas do editor, dê o nome `MedallionPocRuntime` e selecione **Create policy**. Ela permite objetos apenas no bucket da POC, consultas no workgroup `primary` e metadados no banco `medallion_it_tickets_poc`.
2. Repita com `data/staging/iam_poc_bootstrap_policy.json`, com nome `MedallionPocBootstrap`. Essa política permite criar o orçamento `medallion-it-tickets-poc` e configurar somente o bucket escolhido. A AWS lista `aws-portal:ViewBilling` e `aws-portal:ModifyBilling` como dependências do acesso a Budgets; essas ações de Billing abrangem mais que o orçamento específico. Por isso a política é **temporária**: remova após o provisionamento e a validação da Sprint 1.

As políticas não criam IAM users, não dão `AdministratorAccess` e não permitem exclusão dos objetos Bronze. A política runtime é uma base para os scripts desta POC; se o Grafana local exigir APIs adicionais, valide o erro específico antes de ampliar permissões.

### B. Criar o usuário

Em **IAM > Users > Create user**:

1. Nome: `medallion-poc-operator`.
2. Ative **Provide user access to the AWS Management Console** (se disponível). Escolha **I want to create an IAM user** quando o console oferecer a opção. Defina senha forte e marque troca no primeiro acesso.
3. Em **Set permissions**, use **Attach policies directly** para esta POC pessoal e selecione `MedallionPocRuntime`, `MedallionPocBootstrap` e a política gerenciada da AWS `SignInLocalDevelopmentAccess`.
4. Revise e crie. Abra o usuário, vá a **Security credentials** e associe MFA antes de usá-lo. Guarde o link de login IAM mostrado no console, normalmente com o ID ou alias da conta.
5. Saia da sessão root/admin e entre como `medallion-poc-operator`. Não crie uma **Access key**: o `aws login` usa o login do console e credenciais temporárias.

Se a interface da sua conta mostrar a **nova experiência AWS** e impedir acesso ao console para IAM users, use o fluxo de **adicionar membro à equipe** indicado nela ou uma identidade existente de console; não gere uma chave permanente para contornar a tela. Consulte a documentação AWS antes de escolher outro mecanismo.

### C. Configurar o perfil no Mac

Na raiz do repositório:

```bash
export PATH="$PWD/.tools/bin:$PATH"
aws --version
aws login --profile medallion-poc
aws sts get-caller-identity --profile medallion-poc
```

Na primeira execução, escolha `us-east-1` quando solicitado e, no navegador, selecione **o usuário IAM recém-criado**, jamais root. O `Arn` do último comando deve terminar em `user/medallion-poc-operator`. O CLI grava a configuração em `~/.aws/config` e as credenciais temporárias em `~/.aws/login/cache`, fora do Git; a sessão dura até 12 horas e pode ser renovada com o mesmo `aws login`. O boto3 usa o mesmo perfil via `--profile medallion-poc`, desde que as dependências de `requirements.txt` (inclusive `boto3[crt]`) estejam instaladas.

### D. Executar a Sprint 1

```bash
export AWS_PROFILE=medallion-poc
export AWS_REGION=us-east-1
export POC_BUCKET="medallion-it-tickets-poc-$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)-$AWS_REGION"
export POC_BUDGET_EMAIL='SEU_EMAIL_REAL'
export POC_BUDGET_USD=5
bash scripts/provision_aws.sh
.venv/bin/python src/ingest_bronze.py \
  --source data/raw/dataset-tickets-multi-lang3-4k.csv \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE"
```

Troque `SEU_EMAIL_REAL` antes de executar. O script cria o orçamento antes do bucket e valida bloqueio público, criptografia e versionamento. Se a chamada falhar com `AccessDenied`, copie **somente a mensagem de erro sem credenciais** para análise. A opção **Activate IAM access** no Billing controla a interface web, não a API de Budgets; não amplie permissões sem verificar a ação negada. Depois que orçamento, bucket e Bronze forem validados, remova `MedallionPocBootstrap` do usuário em **IAM > Users > medallion-poc-operator > Permissions > Remove permissions**.

Para a verificação do CSV e manifesto no S3, use os comandos em `README.md`. A política runtime já inclui `athena-results/` e o catálogo para as sprints seguintes. Não altere o nome do banco/workgroup sem atualizar a política.

## Se sua conta já usa Organizations e Identity Center

Um administrador deve abrir **IAM Identity Center > Multi-account permissions > Permission sets > Create permission set > Custom permission set**, adicionar a política runtime ajustada como **inline policy** ou política gerenciada da conta, criar um permission set `MedallionPocOperator` e atribuí-lo ao seu usuário/grupo em **AWS accounts > [conta pessoal] > Assign users or groups**. Para o bootstrap, o administrador pode criar um permission set temporário com a política bootstrap e removê-lo após a Sprint 1. O Identity Center provisiona as roles IAM automaticamente. Em seguida, no Mac:

```bash
export PATH="$PWD/.tools/bin:$PATH"
aws configure sso --profile medallion-poc
aws sso login --profile medallion-poc
aws sts get-caller-identity --profile medallion-poc
```

O assistente pede a URL de início do portal, a região do Identity Center, conta, permission set, região padrão de dados e nome do perfil. A região do Identity Center pode ser diferente de `us-east-1`; a região padrão para os dados da POC deve ser a escolhida para S3/Athena/Glue. Uma **account instance** do Identity Center não substitui a **organization instance** para permission sets de acesso à conta.

## Fontes oficiais consultadas em 2026-11-08

- [AWS CLI: login com credenciais temporárias do console](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)
- [Boto3: credenciais via login session](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html)
- [Boto3: instalação do extra AWS CRT](https://docs.aws.amazon.com/boto3/latest/guide/quickstart.html#using-the-aws-common-runtime-crt)
- [IAM: criar usuário no console](https://docs.aws.amazon.com/IAM/latest/UserGuide/getting-started-workloads.html)
- [IAM Identity Center: permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/howtocreatepermissionset.html)
- [AWS Billing: acesso IAM ao console versus APIs](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/control-access-billing.html)

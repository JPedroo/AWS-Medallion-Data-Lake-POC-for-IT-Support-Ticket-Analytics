# Acesso AWS para a conta pessoal e para toda a POC

## Escolha de identidade

**Conta pessoal avulsa:** use um usuário IAM humano `medallion-poc-operator` com acesso ao console, MFA e `aws login --profile medallion-poc`. A AWS CLI v2 instalada neste projeto (2.39.6) oferece credenciais temporárias para esse fluxo; o boto3 com o extra AWS CRT também reconhece o perfil. Não é necessário criar uma role IAM separada. Não crie access keys permanentes para este caminho.

**Conta que já usa AWS Organizations com IAM Identity Center:** peça um permission set dedicado à POC e atribua-o ao seu usuário/grupo. O Identity Center cria e mantém a role IAM correspondente; configure `aws configure sso --profile medallion-poc` e `aws sso login --profile medallion-poc`. Não crie a role manualmente.

Não habilite AWS Organizations apenas para esta POC sem conferir o plano da conta: a [AWS informa](https://docs.aws.amazon.com/singlesignon/latest/userguide/enable-identity-center.html) que, em uma conta Free Tier, criar uma organização pode migrá-la para um plano pago e encerrar créditos Free Tier. A instância de conta isolada do Identity Center não oferece permission sets para acesso à conta AWS.

## Glossário rápido

- **Conta root:** login com o e-mail usado para abrir a conta AWS. Tem acesso irrestrito; use-o somente para preparar o primeiro usuário, caso ainda não exista um administrador.
- **Usuário IAM:** identidade que você criará dentro da conta, chamada `medallion-poc-operator`. Ela terá permissões específicas e fará o trabalho da POC.
- **Política IAM:** arquivo JSON com a lista de permissões. Criar uma política não concede acesso até ela ser anexada ao usuário.
- **Perfil AWS CLI:** nome local, `medallion-poc`, que liga os comandos do Mac ao usuário IAM após `aws login`. Não é uma nova conta ou role.

## Conta pessoal: siga estes passos em ordem

### Passo 1 — Entrar na AWS e localizar o número da conta

1. Abra [console.aws.amazon.com](https://console.aws.amazon.com/) no navegador e faça login. Se você só tem o e-mail e senha usados para abrir a conta, está entrando como **root**. Se já possui um administrador IAM, use esse administrador para os passos 3 a 5.
2. Clique no nome da conta no canto superior direito. Copie o **Account ID**, número de 12 dígitos sem hífens. Este guia usa `us-east-1` para a POC inteira; mantenha essa região em todos os comandos.
3. Se estiver usando root, confirme que ele já tem MFA em **nome da conta > Security credentials > Multi-factor authentication (MFA)**. Se aparecer **Assign MFA device**, configure-o antes de continuar. Você pode usar uma chave de segurança/passkey ou um aplicativo autenticador. [Instruções AWS para proteger root](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html).

### Passo 2 — Gerar os dois arquivos de política no Mac

1. Abra o aplicativo **Terminal** do macOS. Cole o comando abaixo e pressione Enter. Ele entra na pasta do projeto:

```bash
cd '/Users/fpereira.joaopedro/Documents/AWS-Medallion-Data-Lake-POC-for-IT-Support-Ticket-Analytics'
```

2. Cole o bloco abaixo. **Antes de pressionar Enter**, substitua somente `SEU_ID_DE_12_DIGITOS` pelo número copiado no passo 1, mantendo as aspas. **Mantenha `123456789012` nos dois comandos `sed`: esse é o número de exemplo que eles devem encontrar nos modelos para trocá-lo pelo seu ID.** Execute uma linha por vez ou cole o bloco inteiro:

```bash
export POC_ACCOUNT_ID='SEU_ID_DE_12_DIGITOS'
mkdir -p data/staging
sed "s/123456789012/$POC_ACCOUNT_ID/g" config/iam_poc_runtime_policy.template.json > data/staging/iam_poc_runtime_policy.json
sed "s/123456789012/$POC_ACCOUNT_ID/g" config/iam_poc_bootstrap_policy.template.json > data/staging/iam_poc_bootstrap_policy.json
python3 -m json.tool data/staging/iam_poc_runtime_policy.json >/dev/null
python3 -m json.tool data/staging/iam_poc_bootstrap_policy.json >/dev/null
```

3. As duas últimas linhas verificam a sintaxe JSON. Confira se o ID digitado tem **exatamente 12 algarismos**. Para verificar que nenhum texto de exemplo ficou nos arquivos, execute:

```bash
if grep -nE '123456789012|SEU_ID_DE_12_DIGITOS' data/staging/iam_poc_*_policy.json; then
  echo 'ERRO: ainda há texto de exemplo; corrija o ID e repita o passo 2.'
else
  echo 'OK: os números de exemplo foram substituídos.'
fi
```

O `grep` sozinho não mostra nada e retorna código 1 quando não encontra o exemplo; **isso significa sucesso nesta checagem**, embora o Terminal possa destacar esse código como erro. O bloco acima imprime `OK` nesse caso. Os arquivos em `data/staging/` ficam fora do Git.

### Passo 3 — Criar a política de execução no console

1. Abra o [console IAM](https://console.aws.amazon.com/iam/). No menu à esquerda, clique em **Policies (Políticas)** e depois **Create policy (Criar política)**.
2. Em **Policy editor**, selecione **JSON**. Apague o exemplo que já estiver no campo.
3. No Terminal, execute `pbcopy < data/staging/iam_poc_runtime_policy.json`. Volte ao navegador, clique no editor JSON e pressione **Command + V**. `pbcopy` apenas copia o arquivo para a área de transferência do Mac.
4. Clique em **Next (Próximo)**. Se houver erro, verifique o ID da conta no arquivo e repita a cópia. No campo **Policy name**, digite `MedallionPocRuntime`; clique em **Create policy**.
5. Você deverá encontrar `MedallionPocRuntime` na lista **Policies**. Ela cobre S3, Athena e Glue previstos na POC.

### Passo 4 — Criar a política temporária de preparação

1. Em **IAM > Policies**, clique novamente em **Create policy > JSON** e apague o exemplo.
2. No Terminal, execute `pbcopy < data/staging/iam_poc_bootstrap_policy.json`. Cole com **Command + V** no editor JSON da AWS.
3. Clique em **Next**, informe **Policy name** `MedallionPocBootstrap` e clique em **Create policy**.
4. Confirme que as **duas** políticas aparecem na lista. `MedallionPocBootstrap` concede as ações necessárias para orçamento e configuração do bucket. Algumas permissões de Billing nela são mais amplas; por isso ela será removida após a Sprint 1.

### Passo 5 — Criar o usuário IAM e ativar MFA

1. Em **IAM > Users (Usuários)**, clique em **Create user (Criar usuário)**. Em **User name**, digite `medallion-poc-operator`.
2. Marque **Provide user access to the AWS Management Console**. Se for perguntado, selecione **I want to create an IAM user**. Defina uma senha forte e marque a troca de senha no primeiro acesso. Guarde a senha em local seguro.
3. Em **Set permissions**, escolha **Attach policies directly**. Pesquise e marque **três políticas**: `MedallionPocRuntime`, `MedallionPocBootstrap` e `SignInLocalDevelopmentAccess` (esta última é gerenciada pela AWS). Avance, revise os três nomes e clique em **Create user**.
4. Guarde o **Console sign-in URL** exibido no final. Se não o encontrar, use `https://SEU_ID_DE_12_DIGITOS.signin.aws.amazon.com/console/`, substituindo o ID. Esse link é para entrar como usuário IAM.
5. Em **IAM > Users > medallion-poc-operator > Security credentials > Multi-factor authentication (MFA)**, clique em **Assign MFA device**. Escolha passkey/chave de segurança, se disponível, ou **Authenticator app**. Para aplicativo, dê um nome ao dispositivo, escaneie o QR code com o celular e digite os dois códigos consecutivos solicitados. Clique em **Add MFA** e confira que o dispositivo aparece no usuário. [Passos oficiais para aplicativo autenticador](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html).
6. **Não crie uma Access key** na aba Security credentials. O login do CLI mais adiante usa credenciais temporárias.

Se a tela não oferecer acesso ao console para IAM users, sua conta pode usar a [nova experiência da AWS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html), que exige **Add team member (Adicionar membro à equipe)**. Nesse caso, pare neste passo e informe qual tela apareceu; o fluxo de login e de permissões será adaptado antes do provisionamento.

### Passo 6 — Entrar como o usuário criado

1. No navegador, saia da sessão root/administrador. Abra o **Console sign-in URL** guardado no passo 5.
2. Informe o nome `medallion-poc-operator`, a senha e o MFA. Se tiver marcado troca de senha, conclua essa etapa. O menu superior direito deverá mostrar o usuário IAM. [Como usuários IAM entram no console](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_sign-in.html).

### Passo 7 — Criar o perfil da AWS CLI no Mac

Volte ao Terminal na pasta do projeto e execute, uma linha por vez:

```bash
export PATH="$PWD/.tools/bin:$PATH"
aws --version
aws login --profile medallion-poc
aws sts get-caller-identity --profile medallion-poc
```

O `aws login` pergunta a região no primeiro uso: digite `us-east-1` ou pressione Enter se esse for o valor padrão. O navegador abrirá uma tela para escolher a sessão; selecione `medallion-poc-operator`. Se ele não abrir, copie o endereço exibido pelo Terminal e abra-o no navegador. No resultado de `get-caller-identity`, confira que `Arn` termina em `user/medallion-poc-operator` e que `Account` é o ID anotado no passo 1. Se aparecer `:root`, saia com `aws logout --profile medallion-poc` e repita o login selecionando o usuário IAM.

O perfil fica em `~/.aws/config`; a sessão temporária é armazenada em `~/.aws/login/cache`, fora do projeto. Após a sessão expirar, repita `aws login --profile medallion-poc`. O boto3 deste projeto usa o mesmo perfil, pois `boto3[crt]` está em `requirements.txt`.

### Passo 8 — Criar orçamento e bucket pela AWS CLI

**Nesta conta, este passo já foi concluído.** Após a Sprint 1, `MedallionPocBootstrap` foi retirada conforme confirmação do usuário; o perfil `medallion-poc` já não deve executar novamente o script de provisionamento. Os comandos abaixo ficam como registro para a configuração inicial em outra conta.

No mesmo Terminal, substitua `SEU_EMAIL_REAL` pelo e-mail em que deseja receber alertas, e execute:

```bash
export AWS_PROFILE=medallion-poc
export AWS_REGION=us-east-1
export POC_BUCKET="medallion-it-tickets-poc-$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)-$AWS_REGION"
export POC_BUDGET_EMAIL='SEU_EMAIL_REAL'
export POC_BUDGET_USD=5
bash scripts/provision_aws.sh
```

O script cria primeiro o orçamento mensal de **US$ 5**, com alertas por e-mail em 80% e 100%, e depois o bucket privado, com bloqueio público, criptografia e versionamento. Um orçamento envia alertas; ele não bloqueia cobranças. Se houver `AccessDenied`, anote a **ação negada** e a mensagem de erro, sem colar senhas/códigos. A opção **Activate IAM access** do Billing controla a interface web, não a API de Budgets.

### Passo 9 — Enviar e conferir o CSV original na Bronze

No mesmo Terminal:

```bash
.venv/bin/python src/fetch_dataset.py
.venv/bin/python src/ingest_bronze.py \
  --source data/raw/dataset-tickets-multi-lang3-4k.csv \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE"
```

Confira CSV e manifesto no S3 com os comandos da seção **Publicar e conferir a Bronze** no `README.md`. Depois da validação, entre no console como administrador, acesse **IAM > Users > medallion-poc-operator > Permissions**, selecione `MedallionPocBootstrap` e clique em **Remove permissions**. Mantenha `MedallionPocRuntime` e `SignInLocalDevelopmentAccess`. Não altere o nome do banco `medallion_it_tickets_poc` nem o workgroup Athena `primary` sem atualizar a política.

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
- [IAM: criar política no editor JSON](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create-console.html)
- [IAM: login do usuário](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_sign-in.html)
- [IAM: ativar MFA virtual](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html)
- [IAM Identity Center: permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/howtocreatepermissionset.html)
- [AWS Billing: acesso IAM ao console versus APIs](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/control-access-billing.html)

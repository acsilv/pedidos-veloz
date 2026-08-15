# Infraestrutura no Google Cloud

Este diretório é um esqueleto executável para uma rede própria e um cluster GKE Autopilot.
O código não é aplicado pelo GitHub Actions e pode gerar cobrança se for executado.

## Uso seguro

1. Crie um bucket GCS para o state e habilite versionamento.
2. Copie `backend.hcl.example` para `backend.hcl` e `terraform.tfvars.example` para
   `terraform.tfvars`.
3. Autentique com `gcloud auth application-default login`.
4. Execute:

```bash
terraform init -backend-config=backend.hcl
terraform fmt -check
terraform validate
terraform plan -out=plano.tfplan
```

Revise o plano antes de qualquer `terraform apply plano.tfplan`. Para um laboratório que será
apagado, altere `proteger_exclusao` para `false` antes do `terraform destroy`.

O state não deve ficar no Git: ele pode conter identificadores e dados sensíveis. Em uma operação
real, o bucket deve ter versionamento, retenção e acesso restrito à conta do pipeline.

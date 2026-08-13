# Deploy no Portainer — otimização evolutiva contínua

**Contexto**: `docs/11-loop-continuo.md` (otimização manual atingiu retornos decrescentes) e
`docs/12-imitation-learning.md` (tentativa de ML por imitação, negativa). Esta pasta contém
os artefatos para rodar `scripts/evolve_policy.py` (CMA-ES sobre o vetor de pesos da
política) de forma contínua num servidor próprio, sem depender desta sessão de
desenvolvimento.

## Por que o engine não vem embutido na imagem

O engine nativo (`vendor/cg/`) tem licença `LicenseRef-PTCG-ABC-Competition-Use-Only`
— uso restrito ao participante da competição, proibida redistribuição a terceiros
(`docs/06-riscos-questoes-abertas.md`, item 3). Para não violar isso, o container
**busca o engine sozinho, com suas próprias credenciais do Kaggle**, em vez de a
gente empacotar/transmitir o `.so` de qualquer jeito. Mantenha o servidor privado
(não exposto publicamente) para respeitar a cláusula de "medidas razoáveis para
impedir acesso de quem não aceitou as regras".

## Passo a passo

1. **Credenciais do Kaggle**: crie um volume Docker `kaggle_creds` e coloque dentro
   um `kaggle.json` (ou `access_token`) válido — mesmo formato usado nesta sessão
   de desenvolvimento. No Portainer: Volumes > Add volume > depois use o
   "Volume Browser" ou monte um container temporário pra copiar o arquivo.
2. **(Opcional) Sync automático com o git**: se quiser que o container suba o
   checkpoint (`data/ml/evolved_weights.json`) de volta pro repositório sozinho,
   defina `GIT_REMOTE`, `GIT_TOKEN` (um Personal Access Token do GitHub com escopo
   `repo`) e `GIT_BRANCH` nas variáveis de ambiente do `stack.yml`. Sem isso, o
   checkpoint fica só no volume `evolve_data` — copie manualmente quando quiser.
3. **Subir a stack**: Portainer > Stacks > Add stack > cole `stack.yml` (ajuste o
   `context`/`dockerfile` se o caminho do repo no seu servidor for diferente) >
   Deploy.
4. **Rotação de decks** (opcional): `DECK_ROTATION` aceita uma lista de caminhos
   de deck separados por espaço — o loop evolui a política contra cada um em
   sequência, rodada após rodada (útil para não overfitar a um só deck).
5. **Acompanhar progresso**: logs do container (Portainer > Containers > Logs)
   mostram `gen NNN fitness_geração=... melhor_global=...` a cada geração.

## Trazendo o resultado de volta (sem sync automático)

```
docker cp <container>:/app/data/ml/evolved_weights.json ./data/ml/evolved_weights.json
```

Depois, valide localmente antes de promover a qualquer coisa:

```
python3 -c "
import json
w = json.load(open('data/ml/evolved_weights.json'))['weights']
print(w)
"
# cole os pesos em agent/policy_ml.py (_WEIGHTS) e rode eval/local_match.py
# contra os arquétipos catalogados antes de cogitar submeter.
```

**Nunca** promova pesos evoluídos direto para `agent/deck.csv`/produção sem essa
validação — a mesma disciplina de todo o resto do projeto (ver `docs/09`, `docs/11`)
vale aqui: só promover com winrate validado, nunca por confiança no processo de
treino sozinho.

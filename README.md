# Memk Java Launcher — Android (baseado no PojavLauncher)

Um kit **real de personalização e compilação** para criar um launcher de Minecraft: Java Edition no Android. Ele reutiliza o código de execução do **Amethyst**, sucessor livre e derivado do **PojavLauncher**, em vez de apresentar apenas uma simulação.

## O que já fiz

- Marca e nome **Memk Java Launcher**.
- Identificador próprio `com.memk.javalauncher` para não sobrescrever o Amethyst.
- Ícone pixelado original, cores verde-água + fundo escuro e cabeçalho na tela inicial, tanto no modo retrato quanto paisagem.
- Mantidas as funcionalidades *da base*: login Microsoft, seleção e download de versões, execução de Java Edition, controles de toque, configuração de renderização, jogos com mods e instalação de arquivos JAR conforme o suporte do motor.
- Fluxo automatizado de geração de um **APK de teste** via GitHub Actions, sem Android Studio local.

> **IMPORTANTE:** Este ZIP contém a **personalização/automação**, não o APK pronto nem o repositório-fonte completo da engine. O workflow baixa o código original e compila um APK. A compilação e a execução ainda precisam ser testadas. É necessário possuir Minecraft: Java Edition na conta Microsoft para jogar; este projeto não inclui Minecraft, contas ou binários piratas.

## Como gerar o APK pelo GitHub (inclusive no celular)

1. Entre em https://github.com/ e crie um **repositório novo** com uma branch `main`.
2. Extraia este ZIP e envie **os arquivos e pastas internos** para a raiz do repositório, preservando `.github/workflows/build-apk.yml` (a pasta `.github` começa com ponto e pode ficar oculta no gerenciador do celular).
3. No repositório, abra **Actions** → **Construir MEMK Java APK** → **Run workflow**. O envio dos arquivos na branch `main` também pode disparar a construção automaticamente.
4. Quando a execução estiver concluída com sucesso, abra a execução e baixe o artefato **MemkJavaLauncher-Android**. Dentro do ZIP do artefato estará `MemkJavaLauncher-debug.apk`.
5. Instale o APK no Android. Por ser uma compilação de teste, o Android pode avisar que foi gerado fora da Play Store.

Se o GitHub pedir para habilitar Actions, habilite na aba Actions do seu repositório. Se a compilação falhar, veja os logs do passo que apresentou erro; a obtenção do JRE no CI depende da disponibilidade dos artefatos públicos do Amethyst.

## Configuração

Edite `config.json` para mudar `app_name` e `application_id`. Atenção: o cabeçalho e o ícone foram desenhados especificamente para a marca MEMK. O script valida nome, pacote e cor antes de aplicar as alterações. O hash de versão `upstream_revision` registra a base inspecionada; se trocar a versão, também atualize o `git checkout` nos scripts/workflow e confira compatibilidade.

## Compilação manual em computador

```sh
bash preparar_local.sh
# Com o Java/SDK/NDK do Android e os runtimes que a base exige:
cd source
bash scripts/languagelist_updater.sh
./gradlew :app_pojavlauncher:assembleDebug
```

O script clona a base fixada e aplica a personalização. **Não execute duas vezes na mesma pasta sem restaurar `source`**; a segunda aplicação interrompe com aviso por segurança. Use o GitHub Actions para automatizar a obtenção do JRE e as ferramentas de compilação.

## Origens, licenças e transparência

- PojavLauncher (projeto original, descontinuado): https://github.com/PojavLauncherTeam/PojavLauncher
- Amethyst Android (continuação/fork): https://github.com/AngelAuraMC/Amethyst-Android
- Base escolhida: branch `v3_openjdk`, commit `28d6e12d68121b7dd75f2e841058a6b7cdfe4a29`.
- Código da engine e seus componentes sujeitos às licenças originais, incluindo **GNU LGPL-3.0** e respectivas dependências. **Não apague os créditos/licenças do repositório ao redistribuir**.
- Os recursos e scripts novos do kit são disponibilizados sob GNU LGPL-3.0 ou versão posterior; imagens originais criadas para o kit, sem usar arte oficial do Minecraft.
- MEMK é um projeto independente, sem afiliação à Mojang, Microsoft, PojavLauncher Team ou AngelAuraMC.

## Estado do projeto

**Primeira versão de desenvolvimento.** A engine do Amethyst é funcional em seus builds oficiais, mas esta customização ainda **não foi compilada nem testada em dispositivo** neste ambiente. Compatibilidade, FPS, mods, controles e login dependem do Android, GPU, versão Minecraft e do resultado do build. Este projeto não garante funcionamento até o APK passar nesses testes.

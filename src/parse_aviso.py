#python,saida!
import json
import re
import storage
import requests
from datetime import datetime, timezone, timedelta

# Codigo do Tipo de Ocorrencia GMUD no SEU ambiente (varia entre ambientes; confira no Desk)
S_TIPO_GMUD = "000150"

#=================================================
# Le uma lista guardada no Storage (lista vazia se nao existir)
def st_ler(o_st, s_chave):
    import json
    o_st.key = s_chave
    r_get = o_st.Get()
    l_ret = []
    try:
        s_val = r_get.get("value", "") if isinstance(r_get, dict) else ""
        if isinstance(s_val, str) and s_val:
            l_ret = json.loads(s_val)
    except Exception:
        l_ret = []
    if not isinstance(l_ret, list):
        l_ret = []
    return l_ret

#=================================================
# Grava uma lista no Storage
def st_gravar(o_st, s_chave, l_valor):
    import json
    o_st.key = s_chave
    o_st.value = json.dumps(l_valor, ensure_ascii=False)
    o_st.Save()

#=================================================
# POST de formulario na API do Desk (Dados=<json>&App=Ticket) com retry curto
def desk_post(s_url, s_token, d_dados):
    import requests
    import json
    import time
    d_form = {"Dados": json.dumps(d_dados, ensure_ascii=False), "App": "Ticket"}
    o_erro = None
    for i_t in range(3):
        try:
            o_r = requests.post(s_url, headers={"Authorization": s_token}, data=d_form, timeout=40)
            return o_r.json()
        except Exception as e:
            o_erro = e
            time.sleep(2)
    raise o_erro

#=================================================
# Nomes dos aprovadores configurados na auto-categoria (texto separado por virgula)
def buscar_aprovadores(s_token, s_autocat):
    import requests
    import json
    import re
    try:
        d_form = {"Dados": json.dumps({"Chave": str(s_autocat)}), "App": "Ticket"}
        o_r = requests.post("https://SEU-PREFIXO.desk.ms/AutoCategorias", headers={"Authorization": s_token}, data=d_form, timeout=40)
        s_lista = str(o_r.json().get("TAutoCategoria", {}).get("AprovacaoUsuarios", ""))
        l_nomes = []
        for s_item in re.findall(r'"\d+"\s*:\s*"([^"]*)"', s_lista):
            s_nome = s_item.split(" - ")[-1]
            s_nome = re.sub(r"\s*\S+@\S+\s*$", "", s_nome).strip()
            if s_nome != "":
                l_nomes.append(s_nome)
        return ", ".join(l_nomes)
    except Exception:
        return ""

#=================================================
# /GMUDs/lista devolve nomes de campo diferentes conforme o filtro (com Pesquisa: Codigo/St/Agendamento;
# sem Pesquisa: CodChamado/NomeStatus/DataAgendamento). Converte tudo para o primeiro formato.
def norm_gmud(d_it):
    d_n = dict(d_it)
    if "Codigo" not in d_n:
        d_n["Codigo"] = d_it.get("CodChamado", "")
    if "St" not in d_n:
        d_n["St"] = d_it.get("NomeStatus", "")
    if "Agendamento" not in d_n:
        d_n["Agendamento"] = d_it.get("DataAgendamento", "")
    if "AgendamentoFim" not in d_n:
        d_n["AgendamentoFim"] = d_it.get("DataAgendamentoFim", "")
    if "NomeGrupoChamado" not in d_n:
        d_n["NomeGrupoChamado"] = d_it.get("NomeGrupo", "")
    if "Solicitante" not in d_n:
        d_n["Solicitante"] = (str(d_it.get("NomeUsuario", "") or "") + " " + str(d_it.get("SobrenomeUsuario", "") or "")).strip()
    return d_n

#=================================================
# Dados da GMUD no formato usado pelo cartao (a partir de uma linha de /GMUDs/lista)
def previa_gmud(d_g, s_aprov):
    import re
    s_exec = str(d_g.get("Operador", "") or "")
    try:
        i_op = int(d_g.get("CodOperador", -1))
    except Exception:
        i_op = -1
    if s_exec == "" or i_op <= 0:
        s_exec = str(d_g.get("NomeGrupoChamado", "") or "nao definido")
    s_res = re.sub(r"<[^>]*>", " ", str(d_g.get("Descricao", "") or ""))
    s_res = re.sub(r"\s+", " ", s_res).strip()
    if len(s_res) > 220:
        s_res = s_res[:220] + "..."
    s_di = str(d_g.get("Agendamento", "") or "")
    s_df = str(d_g.get("AgendamentoFim", "") or "")
    if len(s_di) >= 10 and s_di[4] == "-":
        s_di = s_di[8:10] + "/" + s_di[5:7] + "/" + s_di[0:4]
    if len(s_df) >= 10 and s_df[4] == "-":
        s_df = s_df[8:10] + "/" + s_df[5:7] + "/" + s_df[0:4]
    s_cod = str(d_g.get("Codigo", ""))
    return {
        "numero": s_cod,
        "titulo": str(d_g.get("Assunto", "")),
        "resumo": s_res,
        "solicitante": str(d_g.get("Solicitante", "")),
        "executor": s_exec,
        "periodo": s_di + " " + str(d_g.get("HoraAgendamento", "")) + " a " + s_df + " " + str(d_g.get("HoraAgendamentoFim", "")),
        "aprovadores": s_aprov,
        "link": "https://SEU-PREFIXO.desk.ms/?Ticket#ChamadosSuporte:" + s_cod,
    }

#=================================================
# Cartao adaptativo (Workflows do Teams). s_cabecalho = titulo do cartao; s_aviso = linha extra opcional
def montar_card(d_p, s_cabecalho, s_aviso):
    l_body = [
        {"type": "TextBlock", "text": s_cabecalho + d_p["numero"], "weight": "Bolder", "size": "Large", "wrap": True},
        {"type": "TextBlock", "text": d_p["titulo"], "wrap": True, "isSubtle": True},
    ]
    if s_aviso != "":
        l_body.append({"type": "TextBlock", "text": s_aviso, "wrap": True, "weight": "Bolder", "color": "Accent"})
    l_body.append({"type": "TextBlock", "text": d_p["resumo"], "wrap": True})
    l_body.append({"type": "FactSet", "facts": [
        {"title": "Solicitante", "value": d_p["solicitante"]},
        {"title": "Executor", "value": d_p["executor"]},
        {"title": "Período", "value": d_p["periodo"]},
        {"title": "Aprovadores", "value": d_p["aprovadores"]},
    ]})
    d_card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": l_body,
        "actions": [{"type": "Action.OpenUrl", "title": "Abrir chamado", "url": d_p["link"]}],
    }
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": d_card}]}

#=================================================
# Envia a mensagem ao Teams; devolve o codigo HTTP
def enviar_teams(s_url, d_msg):
    import requests
    o_resp = requests.post(s_url, json=d_msg, timeout=30)
    return o_resp.status_code

saida = {"ok": False, "resultado": ""}
try:
    d_ini = memoria.get("BEGIN_init", {})
    d_mp = d_ini.get("MAESTRO_PARAMS", {})
    s_acao = str(d_ini.get("acao", "") or "")
    o_st = storage.Storage(str(d_mp.get("codigo", "") or ""))

    # constantes do Maestro chegam em memoria["CST_..."] (texto)
    s_teams_url = str(memoria.get("CST_TEAMS_URL", "") or "")
    s_teams_ativo = str(memoria.get("CST_TEAMS_ATIVO", "") or "")
    s_lembrete_ativo = str(memoria.get("CST_LEMBRETE_ATIVO", "") or "")
    b_teams_ligado = (s_teams_ativo == "S") and s_teams_url.startswith("https://")

    if s_acao == "ler":
        saida = {
            "ok": True,
            "resultado": "ler",
            "teams_ligado": b_teams_ligado,
            "lembrete_ligado": b_teams_ligado and (s_lembrete_ativo == "S"),
            "decisoes": st_ler(o_st, "decisoes"),
            "lembretes_log": st_ler(o_st, "lembretes_log"),
            "previas": st_ler(o_st, "previas") + st_ler(o_st, "previas_lembrete"),
            "avisados_total": len(st_ler(o_st, "avisados")),
        }
    elif s_acao == "limpar":
        for s_k in ["decisoes", "previas", "previas_lembrete", "avisados", "lembretes", "lembretes_log"]:
            o_st.key = s_k
            o_st.Delete()
        saida = {"ok": True, "resultado": "limpar"}
    elif s_acao == "lembrete":
        # Lembrete diario (cron 07:00): GMUDs em Agendamento/Andamento que COMECAM hoje
        s_hoje = datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d")
        s_sim = str(d_ini.get("data_simulada", "") or "")
        b_simulado = s_sim != ""
        if b_simulado:
            s_hoje = s_sim
        b_lemb_ligado = b_teams_ligado and (s_lembrete_ativo == "S") and (not b_simulado)

        try:
            s_tok = str(memoria["CRON_access_token"]["access_token"])
        except Exception:
            s_tok = ""
        if s_tok == "":
            saida = {"ok": False, "resultado": "erro: token do ambiente indisponivel (CRON_access_token)"}
        else:
            # Limit: sem ele a listagem traz so 15 registros
            d_lista = desk_post("https://SEU-PREFIXO.desk.ms/GMUDs/lista", s_tok, {"Pesquisa": "", "Tatual": "", "StatusSLA": "", "Colunas": [], "Ordem": [], "Limit": "1000"})
            l_root = d_lista.get("root", []) if isinstance(d_lista, dict) else []
            l_lembrados = st_ler(o_st, "lembretes")
            d_cache_ac = {}
            l_itens = []
            l_pv = []
            for d_bruto in l_root:
                d_it = norm_gmud(d_bruto)
                if str(d_it.get("Agendamento", "")) != s_hoje:
                    continue
                if str(d_it.get("St", "")) not in ("Agendamento", "Andamento"):
                    continue
                s_chv = str(d_it.get("Chave", ""))
                s_cod = str(d_it.get("Codigo", ""))
                s_marca = s_chv + "|" + s_hoje
                if (s_marca in l_lembrados) and (not b_simulado):
                    l_itens.append({"chamado": s_cod, "resultado": "ignorado: lembrete de hoje ja enviado"})
                    continue
                d_det = desk_post("https://SEU-PREFIXO.desk.ms/GMUDs", s_tok, {"Chave": s_chv})
                s_ac = str(d_det.get("TChamado", {}).get("CodAutoCat", "") or "")
                if s_ac not in d_cache_ac:
                    d_cache_ac[s_ac] = buscar_aprovadores(s_tok, s_ac)
                d_previa = previa_gmud(d_it, d_cache_ac[s_ac])
                if not b_lemb_ligado:
                    l_itens.append({"chamado": s_cod, "resultado": "previa (lembrete desligado ou simulado)", "preview": d_previa})
                    l_pv.append(d_previa)
                else:
                    d_msg = montar_card(d_previa, "Lembrete: GMUD hoje - ", "Execução prevista para hoje. Fique atento ao período abaixo.")
                    i_http = enviar_teams(s_teams_url, d_msg)
                    if i_http in (200, 201, 202):
                        l_itens.append({"chamado": s_cod, "resultado": "lembrete enviado ao Teams"})
                        l_lembrados.append(s_marca)
                    else:
                        l_itens.append({"chamado": s_cod, "resultado": "erro: Teams respondeu HTTP " + str(i_http)})
            if b_lemb_ligado:
                st_gravar(o_st, "lembretes", l_lembrados[-300:])
            if len(l_pv) > 0:
                l_old = st_ler(o_st, "previas_lembrete")
                st_gravar(o_st, "previas_lembrete", (l_old + l_pv)[-5:])
            # registro proprio do lembrete (ultimas 30 execucoes), separado do log de aprovacoes
            l_lg = st_ler(o_st, "lembretes_log")
            l_lg.append({
                "quando": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
                "data": s_hoje,
                "simulado": b_simulado,
                "lembrete_ligado": b_lemb_ligado,
                "encontradas": len(l_itens),
                "enviadas": len([d_x for d_x in l_itens if str(d_x.get("resultado", "")).startswith("lembrete enviado")]),
                "chamados": [str(d_x.get("chamado", "")) + ": " + str(d_x.get("resultado", ""))[:40] for d_x in l_itens][:10],
            })
            st_gravar(o_st, "lembretes_log", l_lg[-30:])
            d_diag = {"tipo_lista": str(type(d_lista)), "total_lista": len(l_root)}
            if isinstance(d_lista, dict):
                d_diag["chaves_resposta"] = sorted(list(d_lista.keys()))[:8]
                d_diag["erro_api"] = str(d_lista.get("erro", ""))[:120]
            if len(l_root) > 0:
                d_ex = norm_gmud(l_root[0])
                d_diag["exemplo"] = {"Codigo": str(d_ex.get("Codigo", "")), "St": str(d_ex.get("St", "")), "Agendamento": str(d_ex.get("Agendamento", ""))}
            saida = {"ok": True, "resultado": "lembrete: " + str(len(l_itens)) + " GMUD(s) para " + s_hoje, "hoje": s_hoje, "itens": l_itens, "teams_ligado": b_teams_ligado, "lembrete_ligado": b_lemb_ligado, "diag": d_diag}
    else:
        # content pode chegar como objeto ou como texto JSON
        d_ct = d_ini.get("content")
        if isinstance(d_ct, str):
            try:
                d_ct = json.loads(d_ct)
            except Exception:
                d_ct = {}
        if not isinstance(d_ct, dict):
            d_ct = {}

        s_chamado = str(d_ct.get("chamado", "") or "")
        s_chamado_cod = str(d_ct.get("chamado_cod", "") or "")
        s_resultado = ""
        d_previa = {}
        # ganchos de teste: sem_envio="S" nunca envia, ignora a deduplicacao e nao grava nada;
        # agora_simulada="AAAA-MM-DD HH:MM" simula o relogio (so vale junto com sem_envio)
        b_sem_envio = str(d_ini.get("sem_envio", "") or "") == "S"
        s_agora_sim = str(d_ini.get("agora_simulada", "") or "")
        b_envio_ok = b_teams_ligado and (not b_sem_envio)

        if str(d_ini.get("trigger", "")) != "6":
            s_resultado = "ignorado: evento diferente de 6"
        elif str(d_ct.get("aprovreprov", "")) != "A":
            s_resultado = "ignorado: nao e aprovacao (aprovreprov=" + str(d_ct.get("aprovreprov", "")) + ")"
        elif str(d_ct.get("tocorrencia_cod", "")) != S_TIPO_GMUD:
            s_resultado = "ignorado: nao e GMUD"
        elif s_chamado_cod == "" or s_chamado == "":
            s_resultado = "ignorado: payload sem chamado"
        elif (s_chamado_cod in st_ler(o_st, "avisados")) and (not b_sem_envio):
            s_resultado = "ignorado: GMUD ja avisada"
        else:
            try:
                s_tok = str(memoria["CRON_access_token"]["access_token"])
            except Exception:
                s_tok = ""
            if s_tok == "":
                s_resultado = "erro: token do ambiente indisponivel (CRON_access_token)"
            else:
                d_lista = desk_post("https://SEU-PREFIXO.desk.ms/GMUDs/lista", s_tok, {"Pesquisa": s_chamado, "Tatual": "", "StatusSLA": "", "Colunas": [], "Ordem": []})
                l_root = d_lista.get("root", []) if isinstance(d_lista, dict) else []
                d_g = {}
                for d_it in l_root:
                    if str(d_it.get("Codigo", "")) == s_chamado:
                        d_g = d_it
                if not d_g:
                    s_resultado = "erro: GMUD nao encontrada na listagem"
                else:
                    d_det = desk_post("https://SEU-PREFIXO.desk.ms/GMUDs", s_tok, {"Chave": s_chamado_cod})
                    d_tc = d_det.get("TChamado", {}) if isinstance(d_det, dict) else {}
                    if str(d_tc.get("RequerAprovacao", "")) != "AU":
                        s_resultado = "ignorado: aprovacao parcial (RequerAprovacao=" + str(d_tc.get("RequerAprovacao", "")) + ", aprovaram " + str(d_tc.get("QtsAprovaram", "")) + " de " + str(d_tc.get("QtsAprovam", "")) + ")"
                    else:
                        # Aprovacao final que chega DEPOIS da GMUD acontecer nao deve alertar o grupo:
                        # GMUD ja encerrada (Resolvido/Cancelado) ou janela de execucao ja terminada
                        s_st_atual = str(d_g.get("St", "") or "")
                        b_janela_fim = False
                        try:
                            s_fim = str(d_g.get("AgendamentoFim", "") or "")
                            s_hf = str(d_g.get("HoraAgendamentoFim", "") or "")
                            if len(s_fim) >= 10 and len(s_hf) >= 4:
                                dt_fim = datetime.strptime(s_fim[0:10] + " " + s_hf[0:5], "%Y-%m-%d %H:%M")
                                if b_sem_envio and s_agora_sim != "":
                                    dt_agora = datetime.strptime(s_agora_sim, "%Y-%m-%d %H:%M")
                                else:
                                    dt_agora = datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)
                                b_janela_fim = dt_agora > dt_fim
                        except Exception:
                            b_janela_fim = False

                        if s_st_atual in ("Resolvido", "Cancelado"):
                            s_resultado = "ignorado: GMUD ja encerrada (status " + s_st_atual + ")"
                        elif b_janela_fim:
                            s_resultado = "ignorado: aprovacao concluida depois do fim da janela da GMUD"
                        else:
                            s_aprov = buscar_aprovadores(s_tok, str(d_ct.get("assunto_cod", "")))
                            if s_aprov == "":
                                s_aprov = str(d_ct.get("usuario_aprovador", "") or "")
                            d_previa = previa_gmud(d_g, s_aprov)

                            if not b_envio_ok:
                                s_resultado = "previa gerada (envio ao Teams desligado ou em teste)"
                                if not b_sem_envio:
                                    l_pv = st_ler(o_st, "previas")
                                    l_pv.append(d_previa)
                                    st_gravar(o_st, "previas", l_pv[-5:])
                            else:
                                d_msg = montar_card(d_previa, "GMUD aprovada: ", "")
                                i_http = enviar_teams(s_teams_url, d_msg)
                                if i_http in (200, 201, 202):
                                    s_resultado = "aviso enviado ao Teams"
                                    l_av = st_ler(o_st, "avisados")
                                    l_av.append(s_chamado_cod)
                                    st_gravar(o_st, "avisados", l_av[-200:])
                                else:
                                    s_resultado = "erro: Teams respondeu HTTP " + str(i_http)

        # aprovacoes de chamados que nao sao GMUD nao entram no log (so geram ruido); testes (sem_envio) tambem nao
        if (s_resultado != "ignorado: nao e GMUD") and (not b_sem_envio):
            l_dec = st_ler(o_st, "decisoes")
            l_dec.append({
                "quando_utc": datetime.now(timezone.utc).isoformat(),
                "chamado": s_chamado,
                "aprovreprov": str(d_ct.get("aprovreprov", "")),
                "tocorrencia": str(d_ct.get("tocorrencia_cod", "")),
                "resultado": s_resultado,
            })
            st_gravar(o_st, "decisoes", l_dec[-30:])
        saida = {"ok": True, "resultado": s_resultado, "chamado": s_chamado, "preview": d_previa, "teams_ligado": b_teams_ligado}
except Exception as e:
    saida = {"ok": False, "resultado": "erro", "erro": str(e)[:300]}

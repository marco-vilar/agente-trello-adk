from google.adk.agents.llm_agent import Agent
from google.adk.models import Gemini

from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime

from zoneinfo import ZoneInfo

import os

load_dotenv()

API_KEY = os.getenv('TRELLO_API_KEY')
API_SECRET = os.getenv('TRELLO_API_SECRET')
TOKEN = os.getenv('TRELLO_TOKEN')

def get_temporal_context():
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    return now.strftime('%Y/%m/%d %H:%M:%S')

def ajustar_data_trello(due_date: str):
    data = datetime.strptime(due_date, "%Y-%m-%d")

    data_brasilia = data.replace(
        hour=12,
        minute=0,
        second=0,
        tzinfo=ZoneInfo("America/Sao_Paulo")
    )

    data_utc = data_brasilia.astimezone(ZoneInfo("UTC"))

    return data_utc.isoformat()




def adicionar_tarefa(nome_da_task: str, descricao_da_task: str, due_date: str):

    client = TrelloClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        token=TOKEN
    )

    boards = client.list_boards()
    meu_board = [b for b in boards if b.name == 'DIO'][0]

    listas = meu_board.list_lists()

    minha_lista = [
        l for l in listas
        if l.name.upper() == 'TO DO' or l.name.upper() == 'A FAZER'
    ][0]
    
    due_date_ajustada = ajustar_data_trello(due_date)

    minha_lista.add_card(
        name=nome_da_task,
        desc=descricao_da_task,
        due=due_date_ajustada
    )

def listar_tarefas(status: str = "todas"):
    client = TrelloClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        token=TOKEN
    )

    boards = client.list_boards()
    meu_board = [b for b in boards if b.name == 'DIO'][0]
    listas = meu_board.list_lists()

    if status.lower() == "todas":
        listas_filtradas = listas
    elif status.lower() == "a fazer":
        listas_filtradas = [l for l in listas if l.name.upper() in ['A FAZER', 'TO DO', 'TODO']]
    elif status.lower() == "em andamento":
        listas_filtradas = [l for l in listas if l.name.upper() in ['EM ANDAMENTO', 'DOING']]
    elif status.lower() == "concluido":
        listas_filtradas = [l for l in listas if l.name.upper() in ['CONCLUÍDO', 'CONCLUIDO', 'DONE']]
    else:
        listas_filtradas = listas

    tarefas = []

    for lista in listas_filtradas:
        cards = lista.list_cards()
        for card in cards:
            tarefas.append({
                "nome": card.name,
                "descricao": card.desc,
                "vencimento": card.due,
                "status": lista.name,
                "id": card.id
            })

    return tarefas


def mudar_status_tarefa(nome_da_task: str, novo_status: str) -> str:
    try:
        client = TrelloClient(
            api_key=API_KEY,
            api_secret=API_SECRET,
            token=TOKEN
        )

        boards = client.list_boards()
        meu_board = [b for b in boards if b.name == 'DIO'][0]
        listas = meu_board.list_lists()

        status_map = {
            "a fazer": "A FAZER",
            "em andamento": "EM ANDAMENTO",
            "concluido": "CONCLUÍDO"
        }

        nome_lista_destino = status_map.get(novo_status.lower())

        if not nome_lista_destino:
            return "❌ Status inválido. Use: 'a fazer', 'em andamento' ou 'concluido'"

        lista_destino = next(
            (l for l in listas if l.name.upper() == nome_lista_destino.upper()),
            None
        )

        if not lista_destino:
            return f"❌ Lista '{nome_lista_destino}' não encontrada no board"

        card_encontrado = None
        lista_origem = None

        for lista in listas:
            cards = lista.list_cards()
            card_encontrado = next(
                (c for c in cards if c.name.lower() == nome_da_task.lower()),
                None
            )

            if card_encontrado:
                lista_origem = lista
                break

        if not card_encontrado:
            return f"❌ Card '{nome_da_task}' não encontrado"

        card_encontrado.change_list(lista_destino.id)

        return f"✅ '{nome_da_task}': {lista_origem.name} → {lista_destino.name}"

    except Exception as e:
        return f"❌ Erro: {str(e)}"


def remover_tarefa(nome_da_task: str) -> str:
    try:
        client = TrelloClient(
            api_key=API_KEY,
            api_secret=API_SECRET,
            token=TOKEN
        )

        boards = client.list_boards()
        meu_board = [b for b in boards if b.name == 'DIO'][0]

        listas = meu_board.list_lists()

        for lista in listas:
            cards = lista.list_cards()

            card_encontrado = next(
                (c for c in cards if c.name.lower() == nome_da_task.lower()),
                None
            )

            if card_encontrado:
                card_encontrado.delete()
                return f"✅ Tarefa '{nome_da_task}' removida com sucesso."

        return f"❌ Tarefa '{nome_da_task}' não encontrada."

    except Exception as e:
        return f"❌ Erro ao remover tarefa: {str(e)}"




root_agent = Agent(
    model=Gemini(model='gemini-3.5-flash-lite'),
    name='root_agent',
    description='Agente de Organização de Tarefas',
    instruction="""
        Você é um agente de organização de tarefas.
        Use as ferramentas somente quando forem necessárias.

        Regras:
        1. Se o usuário pedir para listar tarefas, use apenas listar_tarefas.
        2. Se o usuário pedir para adicionar uma tarefa, use apenas adicionar_tarefa.
        3. Se o usuário pedir para mudar o status de uma tarefa, use apenas mudar_status_tarefa.
        4. Use get_temporal_context somente quando o usuário perguntar a data/hora
   ou quando iniciar explicitamente o planejamento das tarefas do dia.
        5. Não consulte a data ao listar, criar ou mover tarefas, a menos que seja necessária.
        6. Não repita chamadas de ferramentas se já tiver obtido a informação necessária.
        7. Seja breve nas respostas.
        8. Permita remover uma tarefa quando o usuário solicitar explicitamente.
    """,
    tools=[
        get_temporal_context,
        adicionar_tarefa,
        listar_tarefas,
        mudar_status_tarefa,
        remover_tarefa
    ],
)
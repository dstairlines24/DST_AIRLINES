import dash
from dash import dcc, html, Input, Output
import dash_table
import plotly.express as px
import pandas as pd
from pymongo import MongoClient
import os

#==========================================================
# Connexion à MongoDB et chargement des données
#==========================================================
def load_data():
    # Récupérer l'URI de MongoDB depuis la variable d'environnement
    mongo_uri = os.getenv("MONGO_URI")
    
    # Connexion à MongoDB
    client = MongoClient(mongo_uri)
    db = client.app_data
    
    # Création du DataFrame pandas
    df = pd.DataFrame(list(db['final_flights'].find()))
    
    # Appliquer les transformations
    from scripts.ml_data_transform import DataTransform
    datatransform = DataTransform(df)
    df = datatransform.apply_feat_transforms()
    df = datatransform.apply_target_transforms()

    # Filtrer les colonnes 'target_' et 'feat_'
    target_feat_columns = [col for col in df.columns if col.startswith('target_') or col.startswith('feat_')]
    filtered_df = df[target_feat_columns]
    
    return target_feat_columns, filtered_df


# Application Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Mon Application Dash"

# Charger les données au démarrage
target_feat_columns, filtered_df = load_data()

# Mise en page avec dcc.Tabs pour la navigation
app.layout = html.Div([
    html.H1("Application Dash avec Navigation par Tabs"),

    # Stocker les données dans dcc.Store
    dcc.Store(id='stored-data', data={'columns': target_feat_columns, 'filtered_df': filtered_df.to_dict('records')}), 

    dcc.Tabs(id="tabs", value='table-tab', children=[
        dcc.Tab(label='Colonnes Target_ et feat_', value='table-tab'),
        dcc.Tab(label='Scatter Plot', value='scatter-tab'),
    ]),
    html.Div(id='tabs-content')
])

# Layout de la table
table_layout = html.Div([
    html.H2("Colonnes Target_ et feat_"),

    html.Div([
        html.Button("Tout cocher", id='check-all', n_clicks=0),
        html.Button("Tout décocher", id='uncheck-all', n_clicks=0),
    ], style={'marginBottom': '20px', 'display': 'inline-block'}),

    html.Div([
        html.Label("Sélectionnez les colonnes à afficher :"),
        dcc.Checklist(
            id='column-selector',
            options=[{'label': col, 'value': col} for col in target_feat_columns],  # Options initialisées ici
            value=target_feat_columns,  # Affiche toutes les colonnes par défaut
            inline=True
        )
    ], style={'marginBottom': '20px'}),

    # Nouvelle table pour les statistiques
    html.H3("Statistiques des colonnes sélectionnées"),
    dash_table.DataTable(
        id='statistics-table',
        columns=[],  # Les colonnes seront mises à jour dynamiquement
        data=[],  # Initialement vide, sera mis à jour par un callback
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
    ),

    # Table de données filtrées
    dash_table.DataTable(
        id='filtered-table',
        columns=[],  # Les colonnes seront mises à jour dynamiquement
        data=[],  # Initialement vide, sera mis à jour par un callback
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
        sort_action="native",
        sort_mode="multi"
    )
])

# Layout du Scatter Plot
scatter_layout = html.Div([
    html.H2("Scatter Plot"),

    html.Div([
        html.Label("Axe des X :"),
        dcc.Dropdown(
            id='x-axis-dropdown',
            options=[{'label': col, 'value': col} for col in target_feat_columns],  # Initialiser les options ici
            placeholder="Sélectionnez une colonne pour l'axe des X"
        ),
    ], style={'marginBottom': '10px'}),

    html.Div([
        html.Label("Axe des Y :"),
        dcc.Dropdown(
            id='y-axis-dropdown',
            options=[{'label': col, 'value': col} for col in target_feat_columns],  # Initialiser les options ici
            placeholder="Sélectionnez une colonne pour l'axe des Y"
        ),
    ], style={'marginBottom': '10px'}),

    html.Div([
        html.Label("Taille des points :"),
        dcc.Dropdown(
            id='size-dropdown',
            options=[{'label': col, 'value': col} for col in target_feat_columns],  # Initialiser les options ici
            placeholder="Optionnel : Taille des points"
        ),
    ], style={'marginBottom': '10px'}),

    html.Div([
        html.Label("Couleur des points :"),
        dcc.Dropdown(
            id='color-dropdown',
            options=[{'label': col, 'value': col} for col in target_feat_columns],  # Initialiser les options ici
            placeholder="Optionnel : Couleur des points"
        ),
    ], style={'marginBottom': '10px'}),

    dcc.Graph(id='scatter-plot')
])

# Callback pour afficher le contenu du tab sélectionné
@app.callback(Output('tabs-content', 'children'),
              Input('tabs', 'value'))
def render_content(tab):
    if tab == 'table-tab':
        return table_layout
    elif tab == 'scatter-tab':
        return scatter_layout

# Callback pour mettre à jour les colonnes affichées dans la table filtrée et des statistiques
@app.callback(
    Output('filtered-table', 'columns'),
    Output('filtered-table', 'data'),
    Output('statistics-table', 'columns'),
    Output('statistics-table', 'data'),
    Output('column-selector', 'value'),
    Input('stored-data', 'data'),
    Input('column-selector', 'value'),
    Input('check-all', 'n_clicks'),
    Input('uncheck-all', 'n_clicks')
)
def update_table_and_statistics(data, selected_columns, check_all, uncheck_all):
    # Récupérer les données depuis le store
    target_feat_columns = data['columns']
    filtered_df = pd.DataFrame(data['filtered_df'])
    
    # Gérer les actions des boutons "Tout cocher" et "Tout décocher"
    if check_all > uncheck_all:
        selected_columns = target_feat_columns  # Tout cocher
    elif uncheck_all > check_all:
        selected_columns = []  # Tout décocher

    # Mettre à jour la checklist avec les options et la valeur par défaut
    if not selected_columns:
        selected_columns = target_feat_columns  # Si aucune colonne n'est sélectionnée, afficher toutes les colonnes par défaut
    
    # Ajouter la colonne de zéros en première position
    filtered_columns = [{"name": "____________", "id": "zero"}] + [{"name": col, "id": col} for col in selected_columns]
    filtered_data = [{"zero": 0, **row} for row in filtered_df[selected_columns].to_dict('records')]

    # Calculer les statistiques
    stats_data = []
    if selected_columns:
        selected_df = filtered_df[selected_columns]
        
        stats_data.append({"stat": "Moyenne", **{col: selected_df[col].mean() for col in selected_columns}})
        stats_data.append({"stat": "Médiane", **{col: selected_df[col].median() for col in selected_columns}})
        stats_data.append({"stat": "Min", **{col: selected_df[col].min() for col in selected_columns}})
        stats_data.append({"stat": "Max", **{col: selected_df[col].max() for col in selected_columns}})

    # Créer dynamiquement les colonnes de la table des statistiques
    statistics_columns = [{"name": "Statistiques", "id": "stat"}] + [{"name": col, "id": col} for col in selected_columns]

    # Retourner les résultats
    return filtered_columns, filtered_data, statistics_columns, stats_data, selected_columns

@app.callback(
    Output('scatter-plot', 'figure'),
    Input('x-axis-dropdown', 'value'),
    Input('y-axis-dropdown', 'value'),
    Input('size-dropdown', 'value'),
    Input('color-dropdown', 'value'),
    Input('stored-data', 'data')
)
def update_scatter_plot(x_col, y_col, size_col, color_col, data):
    filtered_df = pd.DataFrame(data['filtered_df'])

    if not x_col or not y_col:
        return px.scatter()  # Retourner un graphique vide si x ou y non sélectionné

    fig = px.scatter(
        filtered_df, 
        x=x_col, 
        y=y_col, 
        size=size_col if size_col else None,
        color=color_col if color_col else None,
        title=f'Scatter Plot: {x_col} vs {y_col}'
    )
    fig.update_layout(margin={'l': 40, 'r': 40, 't': 50, 'b': 40})
    return fig


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8051)

from jupyter_dash import JupyterDash
import dash_core_components as dcc
import dash
import dash_html_components as html
import dash_table
import pandas as pd
import os
import flask
import re
import glob
import plotly.express as px
import io
import zipfile


files = zipfile.ZipFile("/content/Dashboard-HNS/Ganesh Q2 2021 HNS2 impact final September.zip")
for file in files.namelist():
  files.extract(file)
files.close()

app = JupyterDash(__name__)

image_directory = "Dashboard-HNS/Figure/"
list_of_images = [os.path.basename(x) for x in glob.glob('{}*.jpg'.format(image_directory))]
static_image_route = '/static/'

HNS_path= "Dashboard-HNS/HNS Standards.xlsx"
HNS_df = pd.read_excel(HNS_path)

path = "Dashboard-HNS/comliance change.csv"
df = pd.read_csv(path)

nutrition_df = pd.read_csv("Ganesh Q2 2021 HNS2 impact final September.csv")

available_indicators = ["Energy", "SAFA", "Sugar", "Sodium"]

app.layout = html.Div(children=[
    html.H1(children='Dashboard of HNS2.0 Impact'),
    
    html.Div([
            dcc.Dropdown(
                id='file_name',
                options=[{'label': i.replace(".jpg", ""), 'value': i} for i in list_of_images],
                value='SOUPS.jpg'
            )
        ], style={'width': '100%', 'display': 'inline-block'}),
    dash_table.DataTable(
            id = 'table',
            columns=[{'name': i, 'id': i} for i in HNS_df.columns],
            data = HNS_df.to_dict('records')),
            
    html.Div(id='changes',style={ 'padding': '10px 5px'}),
    html.Div([

        html.Div([
            dcc.Dropdown(
                id='crossfilter-xaxis-column',
                options=[{'label': i, 'value': i} for i in available_indicators],
                value='Sodium'
            )],style={'width': '49%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-yaxis-column',
                options=[{'label': i, 'value': i} for i in available_indicators],
                value='SAFA'
            )], style={'width': '49%', 'float': 'right', 'display': 'inline-block'})
    ], style={'padding': '10px 5px' }),

    html.Div([
        dcc.Graph(
            id='crossfilter-indicator-scatter'
        )
    ], style={'width': '100%', 'display': 'inline-block', 'padding': '0 20'}),
        
#    html.Div([
#        dcc.Slider(
#            min=0,
#            max=25700,
#            step=1,
#            value=165,
#            tooltip={"placement": "bottom", "always_visible": True}
#)], style={'width': '80%', 'float': 'median', 'display': 'inline-block'} ),    
    html.Img(
        id='indicator-graphic',
        sizes="(max-width: 500px) 400px, 500px",
        style={'width': '100%'})
])
@app.callback(
    dash.dependencies.Output('crossfilter-indicator-scatter', 'figure'),
    [dash.dependencies.Input('crossfilter-xaxis-column', 'value'),
     dash.dependencies.Input('crossfilter-yaxis-column', 'value'),
     dash.dependencies.Input('file_name', 'value')])
def update_graph(xaxis_column_name, yaxis_column_name,
                 file_name):
    product_group = file_name.replace(".jpg", "")
    dff = nutrition_df[(nutrition_df['Vitality Product Group 2.0'] == product_group) & (nutrition_df['HNS 2.0 compliance'].isin(["Compliant", "Not compliant"])) ]
    benchmark_dict = {
    "Energy Benchmark/ serve" : "Energy kcal per Serve",
    "Sodium Benchmark/100g" : "Sodium mg per 100g SCORE",
    "Sodium Benchmark/serve" : "Sodium mg per serve",
    "SAFA Benchmark / 100g" : "SAFA g per 100g SCORE",
    "SAFA Benchmark / serve" : "SAFA per Serve",
    "SAFA Benchmark %total fat" : "SAFA % Tot_Fat",
    "Total Sugar Benchmark /100g" : "Tot_Sugar g per 100g SCORE",
    "Total Sugar Benchmark /serve" : "Tot_Sugar per Serve",
    "Added Sugar Benchmark /100g" : "Added Sugar g per 100g SCORE"
    }    
    features = []
    for benchmark in benchmark_dict.keys():
        if sum(dff[benchmark].isna()) == 0:
            features.append(benchmark_dict[benchmark])
    xaxis =  [i for i in features if xaxis_column_name in i][0]
    yaxis =  [i for i in features if yaxis_column_name in i][0]
    x_benchmark = float(re.findall(r'\d+?\.?\d*',(HNS_df[(HNS_df['Product Group']==product_group) & (HNS_df['Nutrients']==xaxis_column_name)]['HNS2.0']).values[0])[0])
    y_benchmark = float(re.findall(r'\d+?\.?\d*',(HNS_df[(HNS_df['Product Group']==product_group) & (HNS_df['Nutrients']==yaxis_column_name)]['HNS2.0']).values[0])[0])
    gdf = dff.groupby('CUC Code').agg({xaxis:'mean', yaxis:'mean', 'Absolute Volume Contribution':'sum',
                                  'HNS compliance changes': lambda x: x.value_counts().index[0]})
    
    fig = px.scatter(gdf, x=xaxis,
            y=yaxis,
            size = 'Absolute Volume Contribution',
            size_max=30,
            color= 'HNS compliance changes',
            color_discrete_map={
                    "Compliant to Compliant": "#00CC96",
                    "Compliant to Not compliant": "red",
                    "Not compliant to Not compliant": "#636EFA",
                    "Missing Data to Not compliant": "goldenrod",
                    "Missing Data to Compliant": "magenta", 
                    "Outlier to Not compliant": "pink"},
            hover_name=gdf.index)

    fig.add_scatter(
        x=[x_benchmark, x_benchmark],
        y=[0,max(gdf[yaxis])], 
        line={
            'color': 'rgb(50, 171, 96)',
            'width': 2,
            'dash': 'dashdot',
        }, name=xaxis_column_name+" benchmark")
    fig.add_scatter(
        x=[0,max(gdf[xaxis])],
        y=[y_benchmark, y_benchmark], 
        line={
            'color': 'rgb(50, 171, 96)',
            'width': 2,
            'dash': 'dashdot',
        }, name=yaxis_column_name+" benchmark")

    fig.update_traces(customdata=gdf)

    fig.update_xaxes(title=xaxis_column_name)

    fig.update_yaxes(title=yaxis_column_name)

    #fig.update_layout(margin={'l': 40, 'b': 40, 't': 10, 'r': 0}, hovermode='closest')

    return fig

@app.callback(
    dash.dependencies.Output('table', 'data'), 
    dash.dependencies.Input('file_name', 'value'))
def update_table(file_name):
    product_group = file_name.replace(".jpg", "")
    if product_group in HNS_df['Product Group'].unique():
        return HNS_df[HNS_df['Product Group']==product_group].to_dict('records')
    else:
        return 
    
@app.callback(
    dash.dependencies.Output('changes', 'children'), 
    dash.dependencies.Input('file_name', 'value'))
def update_changes(file_name):
    product_group = file_name.replace(".jpg", "")
    if product_group in HNS_df['Product Group'].unique():
        filter_df = df[df['Vitality Product Group 2.0']==product_group]
        if not filter_df['benchmark_delta'].isna().any():
            result = filter_df.Change.values[0]
            benchmark_delta = filter_df['benchmark_delta'].values[0]
            groupchange_delta =  filter_df['group_change_delta'].values[0]
            all_delta = filter_df['All'].values[0]
            return "Compliance changes is %d%% (benchmark changing contributes %d%%, \
             groups changing contributs %d%%), %.2f%% of all product groups" % (result*100, benchmark_delta*100, groupchange_delta*100, all_delta*100)
        else:
            return "This is a new product group."
    else:
        return 
    
@app.callback(
    dash.dependencies.Output('indicator-graphic', 'src'),
    dash.dependencies.Input('file_name', 'value'))
def update_figure(file_name):
    return static_image_route + file_name

@app.server.route('{}<image_path>.jpg'.format(static_image_route))
def serve_image(image_path):
    image_name = '{}.jpg'.format(image_path)
    if image_name not in list_of_images:
        raise Exception('"{}" is excluded from the allowed static files'.format(image_path))
    return flask.send_from_directory(image_directory, image_name)

app.run_server(debug=True)

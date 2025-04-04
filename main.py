"""
Created: 2025-03-05

@suthor: Michael
"""
# import libs
import pandas               as pd # for data manipulation
import numpy                as np
import plotly.graph_objects as go # allows high customisation of plotly graphs
import plotly.express       as px # More user friendly as it makes assumptions on data
import streamlit            as st
from datetime               import datetime

# --------------------------------------------------------
# define functions
# --------------------------------------------------------
# Style functions
def style_negative(v, props=''):
    """ Style negative values in dataframe"""
    try: 
        return props if v < 0 else None
    except:
        pass

def style_positive(v, props=''):
    """Style positive values in dataframe"""
    try: 
        return props if v > 0 else None
    except:
        pass

# Utility functions
def audience_simple(country):
    """ Show top countries """
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else:
        return 'Other'

# load data
@st.cache_data
def load_data():
    
    ## Skip the first data row, which is essentially a header containing totals (which are usually contained in a footer. But anyway ...)
    df_agg = pd.read_csv('data/Aggregated_Metrics_By_Video.csv').iloc[1:,:]
    df_agg.columns = ['Video','Video title','Video publish time','Comments added','Shares','Dislikes','Likes',
                        'Subscribers lost','Subscribers gained','RPM(USD)','CPM(USD)','Average % viewed','Average view duration',
                        'Views','Watch time (hours)','Subscribers','Your estimated revenue (USD)','Impressions','Impressions ctr(%)']
    df_agg['Video publish time'] = pd.to_datetime(df_agg['Video publish time'], format= '%b %d, %Y')
    df_agg['Average view duration'] = df_agg['Average view duration'].apply(lambda x: datetime.strptime(x,'%H:%M:%S'))
    df_agg['Avg_duration_sec'] = df_agg['Average view duration'].apply(lambda x: x.second + x.minute*60 + x.hour*3600)
    df_agg['Engagement_ratio'] =  (df_agg['Comments added'] + df_agg['Shares'] +df_agg['Dislikes'] + df_agg['Likes']) / df_agg['Views']
    df_agg['Views / sub gained'] = df_agg['Views'] / df_agg['Subscribers gained']
    df_agg.sort_values('Video publish time', ascending = False, inplace = True)


    df_agg_sub = pd.read_csv('data/Aggregated_Metrics_By_Country_And_Subscriber_Status.csv')
    df_comments = pd.read_csv('data/All_Comments_Final.csv')
    df_time = pd.read_csv('data/Video_Performance_Over_Time.csv')
    df_time['Date'] = pd.to_datetime(df_time['Date'], format= '%d %b %Y')

    return df_agg, df_agg_sub, df_time, df_comments

# create dataframes from the functions
df_agg, df_agg_sub, df_time, df_comments = load_data()

# engineer data
df_agg_diff = df_agg.copy()
metric_date_12mo = df_agg_diff['Video publish time'].max() - pd.DateOffset(months =12)

# Select only numerical columns for median calculation
numerical_cols = df_agg_diff.select_dtypes(include=np.number).columns
median_agg = df_agg_diff[df_agg_diff['Video publish time'] >= metric_date_12mo][numerical_cols].median()

#Don't know if we'll need this yet
numeric_cols = np.array((df_agg_diff.dtypes == 'float64') | (df_agg_diff.dtypes == 'int64'))
df_agg_diff.iloc[:,numeric_cols] = (df_agg_diff.iloc[:,numeric_cols] - median_agg).div(median_agg)

# Calcs for time-series data
## merge daily data with publish data to get delta
df_time_diff = pd.merge(df_time, df_agg.loc[:,['Video','Video publish time']], left_on = 'External Video ID', right_on = 'Video', how = 'left')
df_time_diff['days_published'] = (df_time_diff['Date'] - df_time_diff['Video publish time']).dt.days

## get last 12 months of data rather than all data
date_12mo = df_agg['Video publish time'].max() - pd.DateOffset(months = 12)
df_time_diff_yr = df_time_diff[df_time_diff['Video publish time'] >= date_12mo]

## Get daily view data (first 30), median & percentiles
views_days = pd.pivot_table(df_time_diff_yr, index = 'days_published', values = 'Views', aggfunc = [np.mean, np.median, lambda x: np.percentile(x,80), lambda x: np.percentile(x,20)]).reset_index()
views_days.columns = ['days_published', 'mean_views', 'median_views', '80pct_views', '20pct_views']
views_days = views_days[views_days['days_published'].between(0,30)]
views_cummulative = views_days.loc[:,['days_published', 'median_views', '80pct_views', '20pct_views']]
views_cummulative.loc[:,['median_views', '80pct_views', '20pct_views']] = views_cummulative.loc[:,['median_views', '80pct_views', '20pct_views']].cumsum()

# Build dashboard
st.title('YouTube Dashboard')
add_sidebar = st.sidebar.selectbox('Aggregate or Individual Video Analysis', ('Aggregate Metrics', 'Individual Video Analysis'))
if add_sidebar == 'Aggregate Metrics':
    st.write('Aggregate Metrics')
    df_agg_metrics = df_agg[['Video publish time','Views','Likes','Subscribers','Shares','Comments added','RPM(USD)','Average % viewed',
                            'Avg_duration_sec','Engagement_ratio','Views / sub gained']]
    metric_date_6mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=6)
    metric_date_12mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=12)
    metric_medians6mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_6mo].median()
    metric_medians12mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_12mo].median()

    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]

    count = 0
    for i in metric_medians6mo.index:
        with columns[count]:
            try:
                delta = (metric_medians6mo[i] - metric_medians12mo[i])/metric_medians12mo[i]
                st.metric(label= i, value = round(metric_medians6mo[i],1), delta = "{:.2%}".format(delta))
            except:
                delta = 0
            count += 1
            if count >= 5:
                count = 0
    
    # display table of data
    df_agg_diff['Publish_date'] = df_agg_diff['Video publish time'].apply(lambda x: x.date())
    df_agg_diff_final = df_agg_diff.loc[:,['Video title', 'Publish_date', 'Views', 'Likes', 'Subscribers',
                                           'Avg_duration_sec' , 'Engagement_ratio', 'Views / sub gained']]

    # Extract numeric columnns
#    df_agg_numeric_lst = df_agg_diff_final.median().index.tolist()
    df_agg_numeric_lst = df_agg_diff_final.select_dtypes(include=np.number).columns.tolist()
    df_to_pct = {}
    for i in df_agg_numeric_lst:
        df_to_pct[i] = '{:.1%}'.format

    st.dataframe(df_agg_diff_final.style.hide().applymap(style_negative,props='color:red;').applymap(style_positive,props='color:green;').format(df_to_pct))

else:
    # Individual video analysis
    st.write('Individual Video Analysis')
    video_select = st.selectbox('Select video', df_agg_diff['Video title'].unique())

    # Subscriber analysis
    agg_filtered = df_agg[df_agg['Video title'] == video_select]
    agg_sub_filtered = df_agg_sub[df_agg_sub['Video Title'] == video_select]
    agg_sub_filtered['Country'] = agg_sub_filtered['Country Code'].apply(audience_simple)
    agg_sub_filtered.sort_values('Is Subscribed', inplace = True)

    fig = px.bar(agg_sub_filtered, x = 'Views', y = "Is Subscribed", color = 'Country', orientation = 'h')
    st.plotly_chart(fig)

    # Time series graph
    agg_time_filtered = df_time_diff[df_time_diff['Video Title'] == video_select]
    first_30 = agg_time_filtered[agg_time_filtered['days_published'].between(0,30)]
    first_30 = first_30.sort_values('days_published')

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x = views_cummulative['days_published'], 
                              y = views_cummulative['20pct_views'], 
                              mode = 'lines', 
                              name = '20th perecentile', 
                              line=dict(color='purple', dash='dash')))
    fig2.add_trace(go.Scatter(x = views_cummulative['days_published'], 
                              y = views_cummulative['median_views'], 
                              mode = 'lines', 
                              name = '50th perecentile', 
                              line=dict(color='black', dash='dash')))
    fig2.add_trace(go.Scatter(x = views_cummulative['days_published'], 
                              y = views_cummulative['80pct_views'], 
                              mode = 'lines', 
                              name = '80th perecentile', 
                              line=dict(color='royalblue', dash='dash')))
    fig2.add_trace(go.Scatter(x = first_30['days_published'], 
                              y = first_30['Views'].cumsum(), 
                              mode = 'lines', 
                              name = 'Current Video', 
                              line=dict(color='firebrick', width=8)))
    fig2.update_layout(title='View comparison for first 30 days',
                      xaxis_title = 'Days since Published',
                      yaxis_title = 'Cumulative views')
    st.plotly_chart(fig2)

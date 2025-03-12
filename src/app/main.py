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

## What metrics will be relevant?
## Difference from baseline
## Percent change by video

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
    st.write('Individual Video Analysis')

# st.write (median_agg)

## Total picture
## Individual video

# Improvements
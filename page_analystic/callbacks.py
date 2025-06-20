import dash
from dash import callback
from datetime import date ,datetime, timedelta
from dash.dependencies import Input, Output
from dash import callback_context
from page_analystic.layout import DistanceMonitorApp

layout_analystic = DistanceMonitorApp()

@callback(
    Output('distance-chart', 'figure'),
    Input('start-date', 'date'),
    Input('end-date', 'date'),
    Input('btn-month-last', 'n_clicks'),
    Input('btn-month-now', 'n_clicks'),
    Input('btn-week-now', 'n_clicks'),
    Input('btn-week-last', 'n_clicks'),
    Input('btn-7', 'n_clicks'),
    Input('btn-30', 'n_clicks'),
    Input('btn-365', 'n_clicks'),
    Input('btn-year-now', 'n_clicks'),
    Input('btn-year-last', 'n_clicks'),



)
def update_chart(start_date, end_date, btn_last, btn_now,btn_week_now, btn_week_last, btn_7, btn_30, btn_365,
            btn_year_now, btn_year_last):
    
    
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id in ['start-date', 'end-date']:
        if not start_date or not end_date:
            return dash.no_update
        start_date_obj = datetime.fromisoformat(start_date).date()
        end_date_obj = datetime.fromisoformat(end_date).date()
        layout_analystic.fetch_and_save_distance(start_date_obj, end_date_obj)
    
    elif trigger_id == 'btn-month-last' and btn_last:
        today = date.today()
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1)
        layout_analystic.fetch_and_save_distance(first_day_prev_month, last_day_prev_month)

    elif trigger_id == 'btn-month-now' and btn_now:
        end_date_obj = date.today()
        start_date_obj = end_date_obj.replace(day=1)
        layout_analystic.fetch_and_save_distance(start_date_obj, end_date_obj)

    
    elif trigger_id == 'btn-week-now' and btn_week_now:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        layout_analystic.fetch_and_save_distance(start_of_week, today)

    elif trigger_id == 'btn-week-last' and btn_week_last:
        today = date.today()
        start_of_this_week = today - timedelta(days=today.weekday())  # Monday
        end_of_last_week = start_of_this_week - timedelta(days=1)  # Sunday last week
        start_of_last_week = end_of_last_week - timedelta(days=6)  # Monday last week
        layout_analystic.fetch_and_save_distance(start_of_last_week, end_of_last_week)

    elif trigger_id == 'btn-7' and btn_7:
        today = date.today()
        start = today - timedelta(days=6)
        end = today
        layout_analystic.fetch_and_save_distance(start, end)


    elif trigger_id == 'btn-30' and btn_30:
        today = date.today()
        start = today - timedelta(days=29)
        end = today
        layout_analystic.fetch_and_save_distance(start, end)

    elif trigger_id== 'btn-365' and btn_365:
        today = date.today()
        start = today - timedelta(days=364)
        end = today
        layout_analystic.fetch_and_save_distance(start, end)

    elif trigger_id == 'btn-year-now' and btn_year_now:
        today = date.today()
        start = today.replace(month=1, day=1)
        end = today
        layout_analystic.fetch_and_save_distance(start, end)
    elif trigger_id == 'btn-year-last' and btn_year_last:
        today = date.today()
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31)
        layout_analystic.fetch_and_save_distance(start, end)


    else:
        return dash.no_update

    


    # Chuyển string sang datetime.date
    
    
    return layout_analystic.build_distance_figure()

@callback(
[
Output('btn-week-now', 'outline'),
Output('btn-week-last', 'outline'),
Output('btn-month-now', 'outline'),
Output('btn-month-last', 'outline'),
Output('btn-7', 'outline'),
Output('btn-30', 'outline'),
Output('btn-365', 'outline'),
Output('btn-year-now', 'outline'),
Output('btn-year-last', 'outline'),
],
[
Input('btn-week-now', 'n_clicks'),
Input('btn-week-last', 'n_clicks'),
Input('btn-month-now', 'n_clicks'),
Input('btn-month-last', 'n_clicks'),
Input('btn-7', 'n_clicks'),
Input('btn-30', 'n_clicks'),
Input('btn-365', 'n_clicks'),
Input('btn-year-now', 'n_clicks'),
Input('btn-year-last', 'n_clicks'),
],
prevent_initial_call=True
)
def update_button_styles(*args):
    ctx = callback_context
    if not ctx.triggered:
        # Ban đầu tất cả đều outline (chưa chọn)
        return [True] * 9
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    btn_ids = [
        'btn-week-now', 'btn-week-last', 'btn-month-now', 'btn-month-last',
        'btn-7', 'btn-30', 'btn-365', 'btn-year-now', 'btn-year-last'
    ]
    
    return [btn_id != trigger_id for btn_id in btn_ids]

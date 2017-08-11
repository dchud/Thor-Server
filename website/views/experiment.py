import pandas as pd
import numpy as np
from flask import (
    Blueprint,
    render_template,
    abort, request,
    make_response,
    url_for,
    redirect
)
from flask_login import login_required, current_user
from flask_api import status
# Bokeh imports.
from bokeh.embed import components
from bokeh.models import HoverTool
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
# Thor Server imports.
from ..models import Experiment, Observation
from ..utils import decode_recommendation
from .. import db

experiment = Blueprint("experiment", __name__)
js_resources = INLINE.render_js()
css_resources = INLINE.render_css()


@experiment.route(
    "/experiment/<int:experiment_id>/analysis/delete_pending/",
    methods=["POST"]
)
@login_required
def delete_pending(experiment_id):
    # Query for the corresponding experiment.
    exp = Experiment.query.filter_by(
        id=experiment_id, user_id=current_user.id
    ).first_or_404()
    pending = exp.observations.filter(Observation.pending==True).all()
    for obs in pending:
        db.session.delete(obs)
    db.session.commit()

    return redirect(url_for("experiment.analysis_page",
                            experiment_id=experiment_id))


@experiment.route("/experiment/<int:experiment_id>/history/download/")
@login_required
def download_history(experiment_id):
    # Query for the corresponding experiment.
    experiment = Experiment.query.filter_by(
        id=experiment_id, user_id=current_user.id
    ).first_or_404()
    # Parse the observations into a pandas dataframe.
    dims = experiment.dimensions.all()
    # obs = experiment.observations.filter(Observation.pending==False).all()
    obs = experiment.observations.order_by("id").all()
    X, y = decode_recommendation(obs, dims)
    D = pd.DataFrame(X, columns=[d.name for d in dims])
    D["target"] = y
    D["obs_id"] = [o.id for o in obs]
    D["date"] = [pd.datetime.strftime(o.date, '%Y-%m-%d %H:%M:%S')
                 for o in obs]
    D.set_index('obs_id', inplace=True)
    # Make a comma-separated variables file.
    resp = make_response(D.to_csv())
    resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
    resp.headers["Content-Type"] = "text/csv"

    return resp


@experiment.route("/experiment/<int:experiment_id>/history/")
@login_required
def history_page(experiment_id):
    # Query for the corresponding experiment.
    experiment = Experiment.query.filter_by(
        id=experiment_id, user_id=current_user.id
    ).first_or_404()

    return render_template(
            "experiment.jinja2",
            tab="history",
            experiment=experiment
        )


def make_fig(x, y, x_axis_label="", y_axis_label="", dim_type="linear",
             title="", plot_height=225):
    """Create and return a figure for the given dimension."""
    hover = HoverTool(tooltips=[
        ("id (??)", "$index"),
        ("value", "$x"),
        ("target", "$y"),
        ])
    fig = figure(
        title=title,
        tools=[hover],
        plot_height=plot_height,
        responsive=True,
        x_axis_label=x_axis_label,
        x_axis_type="linear",
        y_axis_label=y_axis_label,
        y_axis_type="log" if dim_type == "logarithmic" else "linear"
    )
    fig.circle(x, y)
    fig.xaxis.visible = False
    fig.toolbar.logo = None
    return fig


@experiment.route("/experiment/<string:name>/analysis/")
@login_required
def analysis_page(experiment_id):
    # Query for the corresponding experiment.
    experiment = Experiment.query.filter_by(
        id=experiment_id, user_id=current_user.id
    ).first()
    # Grab the inputs arguments from the URL.
    args = request.args
    # Sort selector for analysis, only two allowed values.
    selected_sortby = args.get("sortby", "target")
    if selected_sortby == "observation":
        selected_sortby = "id"
    else:
        selected_sortby = "target"

    if experiment:
        dims = experiment.dimensions.all()
        if experiment.observations.filter_by(pending=False).count() > 1:
            obs = experiment.observations.filter_by(
                pending=False
            ).order_by(selected_sortby).all()
            # squeeze three or more dimensions, otherwise stick to 225
            prop_height = 700 // (len(dims) + 1)
            if prop_height < 225:
                plot_height = prop_height
            else:
                plot_height = 225
            # Extract best observation so far.
            X, y = decode_recommendation(obs, dims)
            # d = dims[selected_dim]
            # Visualize.
            figs = [make_fig(range(len(X)), X[:, dims.index(d)],
                             x_axis_label="", y_axis_label=d.name,
                             dim_type=d.dim_type, plot_height=plot_height)
                    for d in dims]
            title = "Objective value, sorted by {}".format(selected_sortby)
            figs.insert(0, make_fig(range(len(X)), [o.target for o in obs],
                                    x_axis_label="", y_axis_label="target",
                                    dim_type="linear", plot_height=plot_height,
                                    title=title))
            script, divs = components(figs)
        else:
            script, divs = "", [""]

        return encode_utf8(
            render_template(
                "experiment.jinja2",
                tab="analysis",
                selected_sortby=selected_sortby,
                experiment=experiment,
                plot_script=script,
                plot_div=divs,
                js_resources=js_resources,
                css_resources=css_resources,
            )
        )
    else:
        abort(404)


@experiment.route("/experiment/<int:experiment_id>/")
@login_required
def overview_page(experiment_id):
    # Query for the corresponding experiment.
    experiment = Experiment.query.filter_by(
        id=experiment_id, user_id=current_user.id
    ).first_or_404()

    dims = experiment.dimensions.all()
    if experiment.observations.filter_by(pending=False).count() > 1:
        obs = experiment.observations.filter_by(
            pending=False
        ).order_by("date").all()
        # Extract best observation so far.
        X, y = decode_recommendation(obs, dims)
        # Visualize.
        cummax = np.maximum.accumulate(y)
        r = np.arange(1, cummax.shape[0] + 1, step=1)
        fig = figure(
            title="Metric Improvement",
            tools="pan,box_zoom,reset",
            plot_height=225,
            responsive=True,
            x_axis_label="Number of Observations",
        )
        fig.line(r, cummax, line_width=2)
        fig.circle(r, y)
        fig.toolbar.logo = None
        script, div = components(fig)
    else:
        script, div = "", ""

    return encode_utf8(
        render_template(
            "experiment.jinja2",
            tab="overview",
            experiment=experiment,
            plot_script=script,
            plot_div=div,
            js_resources=js_resources,
            css_resources=css_resources,
        )
    )


@experiment.errorhandler(404)
def page_not_found(e):
    return render_template("404.jinja2"), status.HTTP_404_NOT_FOUND

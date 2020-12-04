# Copyright 2020 Google LLC.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
r"""Create a visual report of make_examples runtime by region.

Use this script to visualize the runtime-by-region data generated by running
make_examples with --profile_by_region.
"""

from typing import Dict, Sequence, List, Tuple, Text, Any, Union

from absl import app
from absl import flags
import altair as alt
import pandas as pd
import tensorflow as tf

from third_party.nucleus.io import sharded_file_utils

# Altair uses a lot of method chaining, such as
# chart.mark_bar().encode(...).properties(...), so using backslash
# continuation to break this into separate lines makes the code more readable.
# pylint: disable=g-backslash-continuation

VEGA_URL = 'https://storage.googleapis.com/deepvariant/lib/vega'

FLAGS = flags.FLAGS

flags.DEFINE_string(
    'input', None, 'TSV file that was produced when running make_examples '
    'with --profile_by_region. Can be sharded, e.g. /path/runtime@64.tsv.')
flags.DEFINE_string(
    'title', None, 'Title will be shown at the top of the report and will '
    'be used as a prefix for downloaded image files.')
flags.DEFINE_string('output', 'runtime_by_region_report.html',
                    'Path for the output report, which will be an html file.')

RUNTIME_COLUMNS = [
    'get reads', 'find candidates', 'make pileup images', 'write outputs'
]
COUNT_COLUMNS = ['num reads', 'num examples', 'num candidates']

CSS_STYLES = """
<style>
    body {
      font-family: sans-serif;
    }
    .chart-container {
      padding: 30px;
    }
</style>
"""


def read_sharded_profile_tsvs(path_string: str) -> pd.DataFrame:
  """Imports data from a single or sharded path into a pandas dataframe.

  Args:
    path_string: The path to the input file, which may be sharded.

  Returns:
    A dataframe matching the TSV file(s) but with added Task column.
  """
  if sharded_file_utils.is_sharded_file_spec(path_string):
    paths = sharded_file_utils.generate_sharded_filenames(path_string)
  else:
    paths = [path_string]
  list_of_dataframes = []
  for i, path in enumerate(paths):
    if path.startswith('gs://'):
      # Once pandas is updated to 0.24+, pd.read_csv will work for gs://
      # without this workaround.
      with tf.io.gfile.GFile(path) as f:
        d = pd.read_csv(f, sep='\t')
    else:
      d = pd.read_csv(path, sep='\t')
    d['Task'] = i
    list_of_dataframes.append(d)

  return pd.concat(list_of_dataframes, axis=0, ignore_index=True)


def format_runtime_string(raw_seconds: float) -> str:
  """Creates a nice format string from a potentially large number of seconds.

  Args:
    raw_seconds: A number of seconds.

  Returns:
    The seconds divided into hours, minutes, and remaining seconds, formatted
        nicely. For example, 2h3m5.012s.
  """
  minutes, seconds = divmod(raw_seconds, 60)
  hours, minutes = divmod(minutes, 60)
  seconds = round(seconds, 3)
  output = ''
  if hours > 0:
    output += f'{int(hours)}h'
  if minutes > 0:
    output += f'{int(minutes)}m'
  if seconds > 0 or not output:
    output += f'{seconds}s'
  return output


def calculate_totals(df: pd.DataFrame) -> pd.DataFrame:
  """Calculates total runtime, formats it nicely, and sorts by it.

  Args:
    df: A dataframe of runtime profiling numbers.

  Returns:
    The same dataframe with some additional summary columns.
  """
  # 'total runtime' is a simple sum of the runtime columns.
  df['total runtime'] = df[RUNTIME_COLUMNS].sum(axis=1)

  # Create a formatted runtime string for tooltips.
  df['Runtime'] = df['total runtime'].apply(format_runtime_string)

  # Sort by descending total region runtime.
  df.sort_values(by='total runtime', inplace=True, ascending=False)

  return df


def summarize_by_task(df: pd.DataFrame) -> pd.DataFrame:
  """Groups regions to get the total runtime for each task.

  Args:
    df: A dataframe of runtime profiling numbers.

  Returns:
    The dataframe grouped by task.
  """
  by_task = df.groupby(by=['Task']).sum()
  return by_task.reset_index()


def stage_histogram(d: pd.DataFrame, title: str = '') -> alt.Chart:
  """Plots a histogram of runtimes stacked by stage.

  Args:
    d: A dataframe of runtimes, either by region or by task.
    title: A title for the plot.

  Returns:
    An altair chart.
  """
  columns_used = RUNTIME_COLUMNS
  d = d[columns_used]
  return alt.Chart(d).transform_fold(
      RUNTIME_COLUMNS, as_=['Stage', 'runtime_by_stage']) \
    .mark_bar(opacity=0.3) \
    .encode(
        x=alt.X('runtime_by_stage:Q', bin=alt.Bin(maxbins=100),
                title='Runtime (seconds)'),
        y=alt.Y('count()', title='Count of regions', stack=None),
        color=alt.Color('Stage:N', sort=None)
    ).properties(title=title)


def correlation_scatter_charts(d: pd.DataFrame, title: str = '') -> alt.Chart:
  """Produces a grid of scatter plots of runtimes of stages versus covariates.

  Args:
    d: A pandas dataframe of runtime by regions.
    title: A title for the plot.

  Returns:
    An altair chart
  """
  columns_used = ['region', 'total runtime'] + RUNTIME_COLUMNS + COUNT_COLUMNS
  d = d[columns_used]
  return alt.Chart(d).mark_circle(opacity=0.1).encode(
      x=alt.X(alt.repeat('column'), type='quantitative',
              axis=alt.Axis(labelExpr="datum.value + 's'")),
      y=alt.Y(alt.repeat('row'), type='quantitative'),
      tooltip='region'
  ).properties(width=100, height=100) \
  .repeat(
      column=['total runtime'] + RUNTIME_COLUMNS,
      row=COUNT_COLUMNS,
  ).properties(title=title)


def totals_by_stage(d: pd.DataFrame) -> alt.Chart:
  """Plots total runtimes for each stage.

  Args:
    d: A dataframe of runtimes.

  Returns:
    An altair chart.
  """
  stage_totals_series = d.sum()[RUNTIME_COLUMNS]
  stage_totals = pd.DataFrame(
      stage_totals_series, columns=['Runtime (seconds)'])
  stage_totals.reset_index(inplace=True)
  stage_totals = stage_totals.rename(columns={'index': 'Stage'})
  stage_totals['Runtime'] = stage_totals['Runtime (seconds)'].apply(
      format_runtime_string)
  return alt.Chart(stage_totals).mark_bar().encode(
      x='Runtime (seconds)',
      y=alt.Y('Stage', sort=None),
      tooltip=['Runtime'],
      fill=alt.Fill('Stage',
                    sort=None)).properties(title='Overall runtime by stage')


def pareto_by_task_tooltip(row: pd.Series) -> str:
  """For one row of a dataframe, computes a tooltip description.

  Args:
    row: A Pandas Series, one row of a dataframe containing some specific
      cumulative sum columns.

  Returns:
    A string to show as the tooltip for a pareto curve.
  """
  return (f"{row['task cumsum order']:.2f}% of regions "
          f"account for {row['task cumsum fraction']:.2f}% of "
          f"the runtime in task {row['Task']}")


def calculate_pareto_metrics(df_subset: pd.DataFrame) -> pd.DataFrame:
  """Calculates cumulative sums for a subset of a dataframe.

  Args:
    df_subset: A dataframe subset of one task.

  Returns:
    The same dataframe subset with some additional columns.
  """
  # These are the same for all regions in the same task, for the scatter plot:
  df_subset['task total runtime'] = df_subset['total runtime'].sum()
  df_subset['Runtime for task'] = df_subset['task total runtime'].apply(
      format_runtime_string)
  df_subset['task num examples'] = df_subset['num examples'].sum()
  # These are cumulative sums for the pareto curves:
  df_subset['task cumsum fraction'] = df_subset['total runtime'].cumsum(
  ) / df_subset['total runtime'].sum()
  n = len(df_subset)
  df_subset['task cumsum order'] = list(map(lambda x: x / n, range(0, n)))
  df_subset['tooltip'] = df_subset.apply(pareto_by_task_tooltip, axis=1)
  return df_subset


def pareto_and_runtimes_by_task(df: pd.DataFrame) -> alt.Chart:
  """Creates an interactive Pareto curve and scatter plot of task runtimes.

  Tracing each curve shows to what extent a small proportion of long-running
  regions contribute disproportionately to the overall runtime. That is,
  "The longest-running X% of regions account for Y% of the total runtime."
  There is a curve for each task.

  Args:
    df: A dataframe of all regions.

  Returns:
    An altair chart.
  """
  grouped = df.groupby(df['Task'], sort=False)
  df = grouped.apply(calculate_pareto_metrics)

  # Sample along the Pareto curve, ensuring the longest regions are shown.
  if len(df) > 5000:
    x = 1000
    df = pd.concat([df.nlargest(x, 'total runtime'), df.sample(5000 - x)])

  # Limit columns to greatly reduce the size of the html report.
  columns_used = [
      'task cumsum order', 'task cumsum fraction', 'tooltip', 'Task',
      'task total runtime', 'task num examples', 'Runtime for task'
  ]
  df = df[columns_used]

  # Brushing on the task_scatter plot highlights the same tasks in the Pareto
  # curve.
  brush = alt.selection_interval()

  pareto_by_task = alt.Chart(df).mark_line(size=2).encode(
      x=alt.X(
          'task cumsum order',
          title='The longest-runtime X% of regions',
          axis=alt.Axis(format='%')),
      y=alt.Y(
          'task cumsum fraction',
          title='Account for Y% of the total runtime',
          axis=alt.Axis(format='%')),
      tooltip='tooltip',
      color=alt.condition(brush, 'Task:N', alt.value('lightgray'))).properties(
          title='Pareto curve for each task').interactive()

  # This chart needs to use the same dataframe as the first chart to enable the
  # brushing on one to affect the other. Using max(task) for 'text' is a
  # trick that causes bundling by task to avoid showing multiple overlapping
  # points which otherwise make the text look funky.
  task_scatter = alt.Chart(df).mark_point(size=10).encode(
      x=alt.X('max(task total runtime)', title='Runtime (seconds)'),
      y=alt.Y('task num examples:Q', title='Number of examples'),
      color=alt.condition(brush, 'Task:N', alt.value('lightgray')),
      tooltip=['Task', 'Runtime for task']
    ) \
    .properties(title='Total runtime for each task (drag to highlight)') \
    .add_selection(brush)

  return pareto_by_task | task_scatter


def individual_region_bars(small_df: pd.DataFrame,
                           title: Union[str, Dict[str, str]] = '') -> alt.Chart:
  """Makes a stacked bar chart with runtime of each stage for individual regions.

  Args:
    small_df: A dataframe of regions, each of which will be shown as a bar.
    title: A title for the plot. If a dict, it should contain 'title' and/or
      'subtitle'.

  Returns:
    An altair chart.
  """
  columns_used = ['region', 'Runtime'] + RUNTIME_COLUMNS
  d = small_df[columns_used]
  return alt.Chart(d).transform_fold(
      RUNTIME_COLUMNS, as_=['Stage', 'runtime_by_stage']) \
    .mark_bar().encode(
        x=alt.X('region:N', sort=None),
        y=alt.Y('runtime_by_stage:Q', scale=alt.Scale(type='linear'), title='Runtime (seconds)'),
        fill=alt.Fill('Stage:N', sort=None),
        tooltip='Runtime:N'
    ).properties(title=title)


def selected_longest_and_median_regions(df: pd.DataFrame) -> alt.Chart:
  """Creates a stacked bar charts of the top 20 and median 20 regions.

  Args:
    df: A dataframe of all regions.

  Returns:
    An altair chart.
  """
  num_rows = len(df)
  mid = round(num_rows / 2)

  return individual_region_bars(df.iloc[0:20], 'Top runtime regions') \
  | individual_region_bars(df.iloc[mid-10:mid+11], 'Median runtime regions')


def top_regions_producing_zero_examples(df: pd.DataFrame) -> alt.Chart:
  """Creates a chart of the top regions that produced zero examples.

  Args:
    df: A dataframe of all regions.

  Returns:
    An altair chart.
  """
  regions_with_zero_examples = df[df['num examples'] == 0]

  runtime_of_zeros = regions_with_zero_examples['total runtime'].sum() / 3600

  total_runtime = df['total runtime'].sum() / 3600
  subtitle = (
      f'Spent {runtime_of_zeros:.2f} hours processing the '
      f'{len(regions_with_zero_examples)} regions that produced no examples, '
      f'which is {runtime_of_zeros / total_runtime * 100:.2f}% of the total '
      f'runtime of {total_runtime:.2f} hours.')

  return individual_region_bars(
      regions_with_zero_examples.nlargest(50, 'total runtime'),
      title={
          'text': 'The longest-running regions that produced no examples',
          'subtitle': subtitle
      })


def write_to_html_report(charts: List[Dict[Text, alt.Chart]], title: str,
                         subtitle: str, html_output: Any) -> None:
  """Makes the html report with all the charts inserted.

  Args:
    charts: A list of altair chart objects.
    title: The title to show at the top of the report.
    subtitle: The subtitle to show just below the title on the report.
    html_output: a writable file object.

  Returns:
      None. Writes into the html_output file object.
  """
  # Start the HTML document.
  html_output.write('<!DOCTYPE html>\n<html>\n<head>')
  # Add dependencies vega and vega-lite, which render the altair charts.
  html_output.write('<script type="text/javascript" src="{}/vega@5"></script>'
                    '\n'.format(VEGA_URL))
  html_output.write(
      '<script type="text/javascript" src="{}/vega-lite@4.8.1"></script>'
      '\n'.format(VEGA_URL))
  html_output.write(
      '<script type="text/javascript" src="{}/vega-embed@6"></script>'
      '\n'.format(VEGA_URL))
  # Add styles (CSS).
  html_output.write(CSS_STYLES)
  html_output.write('</head>\n<body>')

  html_output.write('<h1>{}</h1>\n'.format(title))
  html_output.write('<h2>{}</h2>\n'.format(subtitle))

  # Make a div containing all the charts.
  html_output.write('<div>')
  for chart in charts:
    html_output.write(
        '<div class="chart-container" id="vis_{}"></div>\n'.format(chart['id']))
  html_output.write('</div>')

  # Add JSON vega specs and hook them up to the divs with VegaEmbed.
  html_output.write('<script>\n')
  for chart in charts:
    html_output.write('var spec_{} = {};\n'.format(chart['id'],
                                                   chart['chart'].to_json()))
    download_filename = '{}_{}'.format(title.replace(' ', '_'), chart['id'])
    embed_options = {'mode': 'vega-lite', 'downloadFileName': download_filename}

    html_output.write('vegaEmbed("#vis_{}", spec_{}, {})\n'.format(
        chart['id'], chart['id'], embed_options))
  html_output.write('</script>\n')

  # Close HTML document.
  html_output.write('</body></html>')


def read_data_and_make_dataframes(
    input_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
  """Loads data from a file into one dataframe as-is and one by task.

  Args:
    input_path: str, path of the input TSV file (may be sharded).

  Returns:
    df: A dataframe with one row per region.
    by_task: A dataframe with one row per task.
  """
  df = read_sharded_profile_tsvs(input_path)
  df = calculate_totals(df)
  by_task = summarize_by_task(df)
  return df, by_task


def make_all_charts(
    df: pd.DataFrame,
    by_task: pd.DataFrame) -> List[Dict[Text, Union[str, alt.Chart]]]:
  """Creates charts and puts them in a list with their ID names.

  Args:
    df: A dataframe with one row per region.
    by_task: A dataframe with one row per task.

  Returns:
    list of dicts, each containing a chart and a descriptive ID.
  """
  charts = [{
      'id': 'total_by_stage',
      'chart': totals_by_stage(by_task)
  }, {
      'id': 'pareto_and_runtimes_by_task',
      'chart': pareto_and_runtimes_by_task(df)
  }, {
      'id': 'histogram_by_task',
      'chart': stage_histogram(by_task, title='Stage runtimes for each task')
  }, {
      'id': 'selected_longest_and_median_regions',
      'chart': selected_longest_and_median_regions(df)
  }, {
      'id': 'zero_examples',
      'chart': top_regions_producing_zero_examples(df)
  }]

  # Altair shows a max of 5000 data points.
  if len(df) <= 5000:
    # With up to 5000 points, just show them all.
    charts.extend([{
        'id': 'histogram',
        'chart': stage_histogram(df, title='Runtime by stage for all regions')
    }, {
        'id': 'scatter_grid',
        'chart': correlation_scatter_charts(df, title='Trends for all regions')
    }])
  else:
    # With too many points, make different subsets to show trends better.
    top_100 = df.nlargest(100, 'total runtime')
    top_5000 = df.nlargest(5000, 'total runtime')

    # Sample the bottom 99% to avoid outliers that obscure general trends.
    bottom_99_percent = df.nsmallest(int(len(df) * .99), 'total runtime')
    if len(bottom_99_percent) > 5000:
      bottom_99_percent = bottom_99_percent.sample(5000)

    charts.extend([{
        'id':
            'histogram_bottom_99_percent',
        'chart':
            stage_histogram(
                bottom_99_percent, title='Regions in the bottom 99% by runtime')
    }, {
        'id':
            'histogram_top_100',
        'chart':
            stage_histogram(
                top_100,
                title='Runtime by stage for top 100 regions by runtime')
    }, {
        'id':
            'scatter_grid_top_5000',
        'chart':
            correlation_scatter_charts(
                top_5000, title='Trends for top 5000 regions by runtime')
    }, {
        'id':
            'scatter_grid_bottom_99_percent',
        'chart':
            correlation_scatter_charts(
                bottom_99_percent, title='Regions in the bottom 99% by runtime')
    }])
  return charts


def make_report(input_path: str, title: str,
                html_output: tf.io.gfile.GFile) -> None:
  """Reads data, creates charts, and composes the charts into an HTML report.

  Args:
    input_path: Path of the input TSV file (or sharded files).
    title: Title to put at the top of the report.
    html_output: Writable file object where output will be written.
  """

  # Load data into pandas dataframes and add summary columns.
  df, by_task = read_data_and_make_dataframes(input_path)

  # Build all the charts.
  charts = make_all_charts(df, by_task)

  # Write a subtitle with some top-level stats.
  subtitle = (f'Totals: {len(df)} regions '
              f'across {len(by_task)} task{"(s)" if len(by_task) > 1 else ""}')

  # Write the HTML report with all the charts.
  write_to_html_report(
      charts=charts, title=title, subtitle=subtitle, html_output=html_output)


def main(argv: Sequence[str]):
  if len(argv) > 1:
    raise app.UsageError(
        'Command line parsing failure: this script does not accept '
        'positional arguments, but found these extra arguments: "{}".'
        ''.format(str(argv[1:])))

  # Add html to the output path if that is not already the suffix.
  if FLAGS.output.endswith('html'):
    output_filename = FLAGS.output
  else:
    output_filename = f'{FLAGS.output}.html'

  # Start HTML document. Using GFile enables writing to GCS too.
  html_output = tf.io.gfile.GFile(output_filename, 'w')
  make_report(
      input_path=FLAGS.input, title=FLAGS.title, html_output=html_output)
  html_output.close()  # Abstracted out the file open/close to enable testing.
  print('Output written to:', output_filename)


if __name__ == '__main__':
  flags.mark_flags_as_required(['input', 'title'])
  app.run(main)
import pickle
from matplotlib import colors, cm
from hydrological_connectivity.processing.model_result_aggregator import ModelResultAggregator
from rasterio.plot import show_hist
from scipy.stats import laplace
import seaborn
import numpy
from matplotlib import pyplot
from rasterio.plot import show
import os.path
import logging
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_squared_log_error
import cmcrameri.cm as cmc


class ModelBenchmarkCards():
    """ Produce histograms for each of the outputs """

    def __init__(self, model_result_aggregator: ModelResultAggregator, output_folder):
        self.model_result_aggregator = model_result_aggregator
        self.output_folder = output_folder

        params_str = ", ".join([f"{val if type(val) is not dict else ' '.join(val.keys())}" for (
            att, val) in self.model_result_aggregator.model_type.depth_model_params.items()])

        if len(params_str) > 0:
            params_str = f"_{params_str}"
        self.prefix = f"{self.model_result_aggregator.model_type.depth_model_type.name}{params_str}"

        self.histogram_name = f"{self.output_folder}{os.path.sep}{self.prefix}_Histogram.png"
        self.combined = []
        self.values = []

    def output_exists(self):
        return os.path.isfile(self.histogram_name)

    def run_model(self):
        self.tasks = self.model_result_aggregator.produce_stats()
        self.display_order = range(0, len(self.tasks))
        self.display_order = [22, 23, 24, 25, 0, 1, 2, 3, 4, 5, 6, 7,
                              8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, ]

    def save_histogram(self):

        seaborn.set_theme(style="darkgrid")
        seaborn.set(font_scale=0.5)
        fig, axes = pyplot.subplots(
            nrows=7, ncols=4, figsize=(8.3-1, 11.7-1), dpi=300, sharex=True)

        fig.suptitle(
            f"Histograms: Hydraulic Model minus {self.prefix} in 0.1m bins")

        self.scene_stats = {}
        self.values = []
        for index in range(0, len(self.display_order)):
            i = self.display_order[index]
            if i >= len(self.tasks):
                continue
            task = self.tasks[i]
            axis = axes[index // 4][index % 4]
            ma = task["stats"].comparison
            unmasked = ma.data[~ma.mask]
            sample_size = len(unmasked) // 10000
            if (sample_size < 10):
                continue

            if (len(unmasked) > 10000):
                datasubset = unmasked[0::sample_size]
            else:
                datasubset = unmasked
            self.values.append(datasubset)
            res = seaborn.histplot(data=datasubset, binrange=(-5, 5),
                                   ax=axis, bins=100, stat='percent')
            prod_desc = str(task["input"].short_description)
            res.set_title(prod_desc)

            params = laplace.fit(unmasked)
            stat_mean = numpy.ma.mean(ma)
            stat_std = numpy.ma.std(ma)
            stat_pcs = numpy.percentile(
                unmasked, [2.5, 15.9, 25, 50, 75, 84.1, 97.5])

            self.scene_stats[prod_desc] = {
                'mean': stat_mean, 'std': stat_std, 'b': params[1], 'perc': stat_pcs}

            axis.text(2, 0.85*(axis.viewLim.ymax-axis.viewLim.ymin),
                      f"\u03bc={stat_mean:.2f}", fontsize=6)
            axis.text(2, 0.75*(axis.viewLim.ymax-axis.viewLim.ymin),
                      f"\u03c3={stat_std:.2f}", fontsize=6)
            axis.text(2, 0.65*(axis.viewLim.ymax-axis.viewLim.ymin),
                      f"b={params[1]:.2f}", fontsize=6)

            if (index % 4) != 0:
                res.set_ylabel(None)

        # Ideal
        datasubset = numpy.zeros(1000)
        axis = axes[6][3]
        res = seaborn.histplot(data=datasubset, binrange=(-5, 5),
                               ax=axis, bins=100, stat='percent', color='darkred')
        res.set_title("Ideal Distribution")
        axis.text(2, 0.85*(axis.viewLim.ymax-axis.viewLim.ymin),
                  f"\u03bc=0.00", fontsize=6)
        axis.text(2, 0.75*(axis.viewLim.ymax-axis.viewLim.ymin),
                  f"\u03c3=0.00", fontsize=6)
        axis.text(2, 0.65*(axis.viewLim.ymax-axis.viewLim.ymin),
                  f"b=0.00", fontsize=6)
        res.set_ylabel(None)

        # Actual Distribution
        if len(self.values) > 1:
            self.combined = numpy.concatenate(self.values)
        elif len(self.values) == 1:
            self.combined = self.values[0]

        if len(self.values) > 0:
            axis = axes[6][2]
            res = seaborn.histplot(data=self.combined, binrange=(-5, 5),
                                   ax=axis, bins=100, stat='percent', color='darkred')
            res.set_title("Overall Distribution")

            params = laplace.fit(self.combined)

            stat_mean = self.combined.mean()
            stat_std = self.combined.std()

            stat_pcs = numpy.nanpercentile(
                self.combined, [2.5, 15.9, 25, 50, 75, 84.1, 97.5])
            self.overall_scene_stats = {
                'mean': stat_mean, 'std': stat_std, 'b': params[1], 'perc': stat_pcs}

            axis.text(2, 0.85*(axis.viewLim.ymax-axis.viewLim.ymin),
                      f"\u03bc={stat_mean:.2f}", fontsize=6)
            axis.text(2, 0.75*(axis.viewLim.ymax-axis.viewLim.ymin),
                      f"\u03c3={stat_std:.2f}", fontsize=6)
            axis.text(2, 0.65*(axis.viewLim.ymax-axis.viewLim.ymin),
                      f"b={params[1]:.2f}", fontsize=6)

            res.set_ylabel(None)
        else:
            self.overall_scene_stats = {}
        #x = numpy.linspace(min(combined), max(combined), 100)
        #print("PARAMS: ", params)
        #pdf_fitted = laplace.pdf(x, params[0], params[1])
        #axis.plot(x, pdf_fitted, color='red')
        # axis.set_xlim([-5,5])

        pyplot.tight_layout()
        fig.subplots_adjust(top=0.95)
        # pyplot.show()
        pyplot.savefig(self.histogram_name)
        pyplot.cla()
        pyplot.clf()
        pyplot.close('all')
        pyplot.close(fig)

    def run_stats(self, truth, prediction, prod_desc):
        comparison_stats = {}
        if len(truth) == 0:
            return comparison_stats
        try:
            comparison_stats['reference_samples'] = numpy.sum(truth != 0.0)
        except:
            logging.exception(
                f"Could not produce reference_samples for {prod_desc}")

        try:
            comparison_stats['prediction_samples'] = numpy.sum(
                prediction != 0.0)
        except:
            logging.exception(
                f"Could not produce prediction_samples for {prod_desc}")

        try:
            comparison_stats['mean_squared_error'] = mean_squared_error(
                truth, prediction)
        except:
            logging.exception(
                f"Could not produce mean_squared_error for {prod_desc}")

        try:
            comparison_stats['mean_absolute_error'] = mean_absolute_error(
                truth, prediction)
        except:
            logging.exception(
                f"Could not produce mean_absolute_error for {prod_desc}")

        try:
            comparison_stats['mean_squared_log_error'] = mean_squared_log_error(
                truth, prediction)
        except:
            logging.exception(
                f"Could not produce mean_squared_log_error for {prod_desc}")

        try:
            comparison_stats['mean_squared_log_error'] = mean_squared_log_error(
                truth, prediction)
        except:
            logging.exception(
                f"Could not produce mean_squared_log_error for {prod_desc}")

        return comparison_stats

    def save_hex_maps(self):
        seaborn.set(font_scale=0.5)

        pyplot.style.use('seaborn-darkgrid')

        fig, axes = pyplot.subplots(
            nrows=7, ncols=4, figsize=(8.3-1, 11.7-1), dpi=300, sharex=True)

        fig.suptitle(
            f"Hexplots: Hydraulic Model minus {self.prefix} in hex bins")

        error_values = []
        truth_values = []

        self.scene_metrics = {}
        for index in range(0, len(self.display_order)):
            # for index in range(0, 2):
            i = self.display_order[index]
            if i >= len(self.tasks):
                continue
            task = self.tasks[i]
            axis = axes[index // 4][index % 4]
            ma = task["stats"].comparison
            unmasked = ma.data[~ma.mask]
            sample_size = len(unmasked) // 1000
            if (sample_size < 10):
                continue

            truth = task["stats"].truth.data[~ma.mask]
            prod_desc = str(task["input"].short_description)

            truth_mask = ~task["stats"].truth.mask[~ma.mask] & (
                ~numpy.isnan(truth)) & (truth > -1000) & (truth < 1000)
            truth_copy = truth[truth_mask]
            unmasked_copy = unmasked[truth_mask]
            predicted_depth = truth_copy - unmasked_copy

            # predict minimum depth of 1mm (still pretty low for log())
            predicted_depth[predicted_depth < 0.001] = 0.001

            logging.info(
                f"Prediction for {prod_desc} min {numpy.min(predicted_depth)}, mean {numpy.mean(predicted_depth)}, max {numpy.max(predicted_depth)}, percentiles {numpy.percentile(predicted_depth, [2.5, 15.9, 25, 50, 75, 84.1, 97.5])}")

            logging.info(
                f"Benchmark for {prod_desc} min {numpy.min(truth_copy)}, mean {numpy.mean(truth_copy)}, max {numpy.max(truth_copy)}, percentiles {numpy.percentile(truth_copy, [2.5, 15.9, 25, 50, 75, 84.1, 97.5])}")

            performance_metrics = {}

            try:
                fstat_in = task["stats"].fstat
                # Area common (Aop)
                Aop = numpy.sum(fstat_in == 3)
                # Area observed by the reference model (Ao)
                Ao = Aop + numpy.sum(fstat_in == 6)
                # Area of modeled inundation area (Ap)
                Ap = Aop + numpy.sum(fstat_in == 5)
                performance_metrics['fstat'] = Aop/(Ao + Ap - Aop)
            except:
                logging.exception(
                    f"Could not produce all metrics for {prod_desc}")

            try:
                performance_metrics['all'] = self.run_stats(
                    truth_copy, predicted_depth, prod_desc)

                performance_metrics['d < 2'] = self.run_stats(
                    truth_copy[truth_copy < 2], predicted_depth[truth_copy < 2], prod_desc)

                performance_metrics['2 <= d < 4'] = self.run_stats(
                    truth_copy[(truth_copy >= 2) & (truth_copy < 4)], predicted_depth[(truth_copy >= 2) & (truth_copy < 4)], prod_desc)

                performance_metrics['d >= 4'] = self.run_stats(
                    truth_copy[truth_copy >= 4], predicted_depth[truth_copy >= 4], prod_desc)
            except:
                logging.exception(
                    f"Could not produce all metrics for {prod_desc}")

            self.scene_metrics[prod_desc] = performance_metrics

            if (sample_size > 1000):
                datasubset_truth = truth[0::sample_size]
                datasubset_error = unmasked[0::sample_size]
            else:
                datasubset_truth = truth
                datasubset_error = unmasked

            truth_values.append(datasubset_truth)
            error_values.append(datasubset_error)
            xmin = -5  # datasubset_error.min()
            xmax = 5  # datasubset_error.max()
            ymin = 0  # datasubset_truth.min()
            ymax = 10  # datasubset_truth.max()

            try:
                axis.hexbin(x=datasubset_error, y=datasubset_truth, cmap=cm.YlOrRd, gridsize=20, linewidths=0.05, extent=[
                    xmin, xmax, ymin, ymax], mincnt=1, bins='log')
            except:
                logging.exception("Could not produce log bins")

            axis.set_title(prod_desc)

            if (index % 4) != 0:
                axis.set_ylabel(None)

        if len(truth_values) > 1:
            combined_truth_values = numpy.concatenate(truth_values)
            combined_error_values = numpy.concatenate(error_values)
        elif len(truth_values) == 1:
            combined_truth_values = truth_values[0]
            combined_error_values = error_values[0]

        if len(truth_values) > 0:
            axis = axes[6][3]
            try:
                axis.hexbin(x=combined_error_values, y=combined_truth_values, cmap=cm.YlOrRd,
                            gridsize=20, linewidths=0.05, extent=[xmin, xmax, ymin, ymax], mincnt=1, bins='log')
            except:
                logging.exception("Could not produce log bins")
            axis.set_title("Overall Distribution")

            axis.set_ylabel(None)

        pyplot.tight_layout()
        fig.subplots_adjust(top=0.95)
        pyplot.savefig(
            f"{self.output_folder}{os.path.sep}{self.prefix}_HexDepthVsMAE.png")
        pyplot.cla()
        pyplot.clf()
        pyplot.close('all')
        pyplot.close(fig)

    def set_map_font_size(self, small=8, medium=10, large=12):
        SMALL_SIZE = small
        MEDIUM_SIZE = medium
        BIGGER_SIZE = large

        pyplot.style.use('seaborn-white')

        # controls default text sizes
        pyplot.rc('font', size=SMALL_SIZE)
        # fontsize of the axes title
        pyplot.rc('axes', titlesize=SMALL_SIZE)
        # fontsize of the x and y labels
        pyplot.rc('axes', labelsize=MEDIUM_SIZE)
        # fontsize of the tick labels
        pyplot.rc('xtick', labelsize=SMALL_SIZE)
        # fontsize of the tick labels
        pyplot.rc('ytick', labelsize=SMALL_SIZE)
        pyplot.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
        # fontsize of the figure title
        pyplot.rc('figure', titlesize=BIGGER_SIZE)

    def save_maps(self):
        self.set_map_font_size(4, 5, 6)
        fig, axes_list = pyplot.subplots(
            nrows=7, ncols=4, figsize=(8.3-1, 11.7-1), dpi=300)

        cmap = cmc.roma
        # cmap = pyplot.get_cmap('RdYlBu')

        for index in range(0, len(self.display_order)):
            i = self.display_order[index]
            if i >= len(self.tasks):
                continue
            task = self.tasks[i]
            axes = axes_list[index // 4][index % 4]
            ma = task["stats"].comparison
            show(ma, ax=axes, transform=task["stats"].comp_transform, interpolation='nearest',
                 cmap=cmap, title=str(task["input"].short_description), vmin=-2, vmax=2)
            axes.tick_params(axis='y', direction='in', pad=-15)
            axes.tick_params(axis='x', direction='in', pad=-15)
            axes.set_xlabel(None)
            axes.set_ylabel(None)
            axes.set_xticklabels([])
            axes.set_yticklabels([])

        fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(
            vmin=-2, vmax=2), cmap=cmap), ax=axes_list[6][3])

        pyplot.tight_layout()
        # pyplot.show()

        pyplot.savefig(
            f"{self.output_folder}{os.path.sep}{self.prefix}_Maps.png")
        pyplot.cla()
        pyplot.clf()
        pyplot.close('all')
        pyplot.close(fig)
        self.set_map_font_size()

    def save_closeup_map(self, selected=6):
        task = self.tasks[selected]

        # show(task["stats"].comparison)
        seaborn.set_theme(style="whitegrid")
        cmap = cmc.roma
        #cmap = pyplot.get_cmap('RdYlBu')

        fig, ax = pyplot.subplots(
            nrows=1, ncols=1, figsize=(8.3-1, 11.7-1), dpi=300)

        show(task["stats"].comparison, transform=task["stats"].comp_transform, interpolation='nearest',
             cmap=cmap, title=str(task["input"].short_description), vmin=-2, vmax=2, ax=ax)

        fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(
            vmin=-2, vmax=2), cmap=cmap), ax=ax, fraction=0.046, pad=0.04)

        # pyplot.show()

        pyplot.savefig(
            f"{self.output_folder}{os.path.sep}{self.prefix}_Map_Detail_{selected}.png")
        pyplot.cla()
        pyplot.clf()
        pyplot.close('all')
        pyplot.close(fig)

    def save_objects(self):
        output = open(
            f'{self.output_folder}{os.path.sep}{self.prefix}_model_benchmark_cards_combined.pkl', 'wb')
        pickle.dump(self.combined, output)
        output.close()
        output = open(
            f'{self.output_folder}{os.path.sep}{self.prefix}_model_benchmark_cards_values.pkl', 'wb')
        pickle.dump(self.values, output)
        output.close()

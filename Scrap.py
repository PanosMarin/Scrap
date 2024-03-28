import os
import numpy as np
import yaml
import json
import logging

class Scrap_Experiment:
    def __init__(self, data_folder:str, config_file: str = None) -> None:
        '''
        Initialisation class
        '''
        self._study_groups = {}
        self._control_groups = {}
        self._controls_study_map = {}
        self._data_folder = data_folder
        self.configure_experiment(config_file)
        self.extract_plates_data()

    def configure_experiment(self, config_file):
        if config_file is None:
            self.remove_outliars = self._remove_outliars_iqr_construct()
            return

        with open(config_file, 'r') as f:
            experiment_config = yaml.safe_load(f)

        if experiment_config['outliar_removing'] is not None:
            if experiment_config['outliar_removing']['method'] == 'IQR':
                self.remove_outliars = self._remove_outliars_iqr_construct(experiment_config['outliar_removing']['lower_percentile'],
                                                                           experiment_config['outliar_removing']['upper_percentile'],
                                                                           experiment_config['outliar_removing']['range'])

    def extract_plates_data(self) -> None:
        '''
        Extracts data from plate
        '''
        experiment_folders = [dir for dir in os.listdir(self._data_folder) if os.path.isdir(f'{self._data_folder}/{dir}')]
        for folder in experiment_folders:
            hem_table = np.genfromtxt(f'{self._data_folder}/{folder}/hem.csv', delimiter=',', dtype=float)
            spot_table = np.genfromtxt(f'{self._data_folder}/{folder}/spot.csv', delimiter=',', dtype=float)
            layout_table = np.genfromtxt(f'{self._data_folder}/{folder}/layout.csv', delimiter=',', dtype=str)
            with open(f'{self._data_folder}/{folder}/plate.yaml', 'r') as f:
                plate_config = yaml.safe_load(f)

            hem_div_spot_table = hem_table/spot_table
            np.savetxt(f'{self._data_folder}/{folder}/debug/devided_table', hem_div_spot_table, delimiter = ",")

            unique_groups = np.unique(layout_table)
            groups = {group:hem_div_spot_table[layout_table == group] for group in unique_groups}
            with open(f'{self._data_folder}/{folder}/debug/groups', 'w') as f:
                f.write(str(groups))

            for group, data in groups.items():
                groups[group] = self.remove_outliars(data)

            study_groups = {study_group:groups[study_group] for study_group in plate_config['groups']['study']}
            with open(f'{self._data_folder}/{folder}/debug/study_groups_filtered', 'w') as f:
                f.write(str(study_groups))
            control_groups = {control_group:groups[control_group] for control_group in plate_config['groups']['control']}
            with open(f'{self._data_folder}/{folder}/debug/control_groups_filtered', 'w') as f:
                f.write(str(control_groups))

            for control_group, control_data in control_groups.items():
                for study_group in plate_config['mapping'][control_group]:
                    study_groups[study_group] = study_groups[study_group]/control_data.mean()
                    try:
                        self._study_groups[study_group].extend(study_groups[study_group])
                    except:
                        self._study_groups[study_group] = study_groups[study_group].tolist()
                with open(f'{self._data_folder}/{folder}/debug/study_groups_normalised', 'w') as f:
                    f.write(str(study_groups))
                
                control_groups[control_group] = control_groups[control_group]/control_data.mean() 
                try:
                    self._control_groups[control_group].extend(control_groups[control_group])
                except:
                    self._control_groups[control_group] = control_groups[control_group].tolist()
                with open(f'{self._data_folder}/{folder}/debug/control_groups_normalised', 'w') as f:
                    f.write(str(control_groups))

        with open(f'{self._data_folder}/control_groups.json', 'w') as f:
            f.write(str(self._control_groups))
        with open(f'{self._data_folder}/study_groups.json', 'w') as f:
            f.write(str(self._study_groups))



    def _remove_outliars_iqr_construct(self, lower_percentile: int = 25, upper_percentile: int = 75, range: float = 1.5):        
        def remove_outliars_iqr_inner(group_data: np.array) -> np.array:
            '''
            Removes outliars from a list
            '''
            Q1 = np.percentile(group_data, lower_percentile)
            Q3 = np.percentile(group_data, upper_percentile)
            IQR = Q3 - Q1
            lower_bound = Q1 - range * IQR
            upper_bound = Q3 + range * IQR
            filtered_group_data = group_data[(group_data >= lower_bound) & (group_data <= upper_bound)]
            return filtered_group_data
        return remove_outliars_iqr_inner


#a = Scrap_Experiment('./data')
b = Scrap_Experiment('./data', './config.yaml')
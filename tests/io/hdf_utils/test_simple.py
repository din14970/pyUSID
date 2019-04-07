# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 15:07:16 2017

@author: Suhas Somnath
"""
from __future__ import division, print_function, unicode_literals, absolute_import
import unittest
import os
import sys
import h5py
import numpy as np
import dask.array as da
import shutil

sys.path.append("../../pyUSID/")
from pyUSID.io import hdf_utils, write_utils, USIDataset

from tests.io import data_utils


if sys.version_info.major == 3:
    unicode = str


class TestSimple(unittest.TestCase):

    def setUp(self):
        data_utils.make_beps_file()
        data_utils.make_sparse_sampling_file()
        data_utils.make_incomplete_measurement_file()
        data_utils.make_relaxation_file()

    def tearDown(self):
        for file_path in [data_utils.std_beps_path,
                          data_utils.sparse_sampling_path,
                          data_utils.incomplete_measurement_path,
                          data_utils.relaxation_path]:
            data_utils.delete_existing_file(file_path)

    def test_copy_region_refs(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        data = np.random.rand(11, 7)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=data)
            h5_dset_dest = h5_f.create_dataset('Target', data=data)
            source_ref = h5_dset_source.regionref[0:-1:2]
            h5_dset_source.attrs['regref'] = source_ref

            hdf_utils.copy_region_refs(h5_dset_source, h5_dset_dest)

            self.assertTrue(np.allclose(h5_dset_source[h5_dset_source.attrs['regref']],
                                        h5_dset_dest[h5_dset_dest.attrs['regref']]))

        os.remove(file_path)

    def test_check_is_main_legal_01(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            expected_dsets = [h5_f['/Raw_Measurement/source_main'],
                              h5_f['/Raw_Measurement/source_main-Fitter_000/results_main'],
                              h5_f['/Raw_Measurement/source_main-Fitter_001/results_main']]
            for dset in expected_dsets:
                self.assertTrue(hdf_utils.check_if_main(dset))

    def test_check_is_main_illegal_01(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            not_main_dsets = [h5_f,
                              4.123,
                              np.arange(6),
                              h5_f['/Raw_Measurement/Position_Indices'],
                              h5_f['/Raw_Measurement/source_main-Fitter_000'],
                              h5_f['/Raw_Measurement/source_main-Fitter_000/Spectroscopic_Indices'],
                              h5_f['/Raw_Measurement/Spectroscopic_Values']]
            for dset in not_main_dsets:
                self.assertFalse(hdf_utils.check_if_main(dset))

    def test_get_source_dataset_legal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_groups = [h5_f['/Raw_Measurement/source_main-Fitter_000'],
                        h5_f['/Raw_Measurement/source_main-Fitter_001']]
            h5_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            for h5_grp in h5_groups:
                self.assertEqual(h5_main, hdf_utils.get_source_dataset(h5_grp))

    def test_get_source_dataset_illegal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            with self.assertRaises(ValueError):
                _ = hdf_utils.get_source_dataset(h5_f['/Raw_Measurement/Misc'])

    def test_get_all_main_legal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            expected_dsets = [h5_f['/Raw_Measurement/source_main'],
                              h5_f['/Raw_Measurement/source_main-Fitter_000/results_main'],
                              h5_f['/Raw_Measurement/source_main-Fitter_001/results_main']]
            main_dsets = hdf_utils.get_all_main(h5_f, verbose=False)
            # self.assertEqual(set(main_dsets), set(expected_dsets))
            self.assertEqual(len(main_dsets), len(expected_dsets))
            self.assertTrue(np.all([x.name == y.name for x, y in zip(main_dsets, expected_dsets)]))


    def test_write_ind_val_dsets_legal_bare_minimum_pos(self):
        num_cols = 3
        num_rows = 2
        sizes = [num_cols, num_rows]
        dim_names = ['X', 'Y']
        dim_units = ['nm', 'um']

        descriptor = []
        for length, name, units in zip(sizes, dim_names, dim_units):
            descriptor.append(write_utils.Dimension(name, units, np.arange(length)))

        pos_data = np.vstack((np.tile(np.arange(num_cols), num_rows),
                              np.repeat(np.arange(num_rows), num_cols))).T
        file_path = 'test_write_ind_val_dsets.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path, mode='w') as h5_f:
            h5_inds, h5_vals = hdf_utils.write_ind_val_dsets(h5_f, descriptor, is_spectral=False)

            data_utils.validate_aux_dset_pair(self,h5_f, h5_inds, h5_vals, dim_names, dim_units, pos_data,
                                              is_spectral=False)

        os.remove(file_path)

    def test_write_ind_val_dsets_legal_bare_minimum_spec(self):
        num_cols = 3
        num_rows = 2
        sizes = [num_cols, num_rows]
        dim_names = ['X', 'Y']
        dim_units = ['nm', 'um']

        descriptor = []
        for length, name, units in zip(sizes, dim_names, dim_units):
            descriptor.append(write_utils.Dimension(name, units, np.arange(length)))

        spec_data = np.vstack((np.tile(np.arange(num_cols), num_rows),
                              np.repeat(np.arange(num_rows), num_cols)))
        file_path = 'test_write_ind_val_dsets.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path, mode='w') as h5_f:
            h5_group = h5_f.create_group("Blah")
            h5_inds, h5_vals = hdf_utils.write_ind_val_dsets(h5_group, descriptor, is_spectral=True)

            data_utils.validate_aux_dset_pair(self, h5_group, h5_inds, h5_vals, dim_names, dim_units, spec_data,
                                          is_spectral=True)
        os.remove(file_path)

    def test_write_ind_val_dsets_legal_override_steps_offsets_base_name(self):
        num_cols = 2
        num_rows = 3
        dim_names = ['X', 'Y']
        dim_units = ['nm', 'um']
        col_step = 0.25
        row_step = 0.05
        col_initial = 1
        row_initial = 0.2

        descriptor = []
        for length, name, units, step, initial in zip([num_cols, num_rows], dim_names, dim_units,
                                                      [col_step, row_step], [col_initial, row_initial]):
            descriptor.append(write_utils.Dimension(name, units, initial + step * np.arange(length)))

        new_base_name = 'Overriden'
        spec_inds = np.vstack((np.tile(np.arange(num_cols), num_rows),
                              np.repeat(np.arange(num_rows), num_cols)))
        spec_vals = np.vstack((np.tile(np.arange(num_cols), num_rows) * col_step + col_initial,
                              np.repeat(np.arange(num_rows), num_cols) * row_step + row_initial))

        file_path = 'test_write_ind_val_dsets.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path, mode='w') as h5_f:
            h5_group = h5_f.create_group("Blah")
            h5_inds, h5_vals = hdf_utils.write_ind_val_dsets(h5_group, descriptor, is_spectral=True,
                                                             base_name=new_base_name)
            data_utils.validate_aux_dset_pair(self, h5_group, h5_inds, h5_vals, dim_names, dim_units, spec_inds,
                                          vals_matrix=spec_vals, base_name=new_base_name, is_spectral=True)
        os.remove(file_path)

    def test_write_ind_val_dsets_illegal(self):
        sizes = [3, 2]
        dim_names = ['X', 'Y']
        dim_units = ['nm', 'um']

        descriptor = []
        for length, name, units in zip(sizes, dim_names, dim_units):
            descriptor.append(write_utils.Dimension(name, units, np.arange(length)))

        file_path = 'test_write_ind_val_dsets.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path, mode='w') as h5_f:
            pass

        with self.assertRaises(ValueError):
            # h5_f should be valid in terms of type but closed
            _ = hdf_utils.write_ind_val_dsets(h5_f, descriptor)

        os.remove(file_path)

    def test_write_reduced_anc_dsets_spec_2d_to_1d(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)
        shutil.copy(data_utils.std_beps_path, duplicate_path)
        with h5py.File(duplicate_path) as h5_f:
            h5_spec_inds_orig = h5_f['/Raw_Measurement/Spectroscopic_Indices']
            h5_spec_vals_orig = h5_f['/Raw_Measurement/Spectroscopic_Values']
            new_base_name = 'Blah'
            # cycle_starts = np.where(h5_spec_inds_orig[0] == 0)[0]
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_spec_inds_orig.parent,
                                                                                   h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig,
                                                                                   'Bias',
                                                                                   basename=new_base_name)

            dim_names = ['Cycle']
            dim_units = ['']
            ref_data = np.expand_dims(np.arange(2), axis=0)
            for h5_dset, exp_dtype, exp_name in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                    [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                    [new_base_name + '_Indices', new_base_name + '_Values']):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_spec_inds_orig.parent)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_write_reduced_anc_dsets_spec_1d_to_0d(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)

        with h5py.File(duplicate_path) as h5_f:

            h5_spec_inds_orig, h5_spec_vals_orig = hdf_utils.write_ind_val_dsets(h5_f,
                                                                                 write_utils.Dimension('Bias', 'V', 10),
                                                                                 is_spectral=True)
            new_base_name = 'Blah'
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_f, h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig,
                                                                                   'Bias', basename=new_base_name)

            dim_names = ['Single_Step']
            dim_units = ['a. u.']
            ref_data = np.expand_dims(np.arange(1), axis=0)
            for h5_dset, exp_dtype, exp_name in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                    [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                    [new_base_name + '_Indices', new_base_name + '_Values']):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_spec_inds_orig.parent)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_write_reduced_anc_dsets_3d_to_1d_pos_fastest_n_slowest(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)

        with h5py.File(duplicate_path) as h5_f:

            dims = [write_utils.Dimension('X', 'nm', np.linspace(300, 350, 5)),
                    write_utils.Dimension('Y', 'um', [-2, 4, 10]),
                    write_utils.Dimension('Z', 'm', 2)]

            h5_spec_inds_orig, h5_spec_vals_orig = hdf_utils.write_ind_val_dsets(h5_f, dims, is_spectral=False)
            new_base_name = 'Position'
            h5_grp = h5_f.create_group('My_Group')
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_grp, h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig, ['X', 'Z'])

            dim_names = ['Y']
            dim_units = ['um']
            ref_inds = np.expand_dims(np.arange(3), axis=1)
            ref_vals = np.expand_dims([-2, 4, 10], axis=1)
            for h5_dset, exp_dtype, exp_name, ref_data in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                              [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                              [new_base_name + '_Indices', new_base_name + '_Values'],
                                                              [ref_inds, ref_vals]):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_grp)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[:, dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_write_reduced_anc_dsets_3d_to_1d_spec_fastest_n_slowest(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)

        with h5py.File(duplicate_path) as h5_f:

            dims = [write_utils.Dimension('Freq', 'Hz', np.linspace(300, 350, 5)),
                    write_utils.Dimension('Bias', 'V', [-2, 4, 10]),
                    write_utils.Dimension('Cycle', 'a.u.', 2)]

            h5_spec_inds_orig, h5_spec_vals_orig = hdf_utils.write_ind_val_dsets(h5_f, dims, is_spectral=True)
            new_base_name = 'Blah'
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_f, h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig,
                                                                                   ['Freq', 'Cycle'],
                                                                                   basename=new_base_name)

            dim_names = ['Bias']
            dim_units = ['V']
            ref_inds = np.expand_dims(np.arange(3), axis=0)
            ref_vals = np.expand_dims([-2, 4, 10], axis=0)
            for h5_dset, exp_dtype, exp_name, ref_data in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                              [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                              [new_base_name + '_Indices', new_base_name + '_Values'],
                                                              [ref_inds, ref_vals]):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_spec_inds_orig.parent)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_write_reduced_anc_dsets_3d_to_1d_spec_fastest(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)

        with h5py.File(duplicate_path) as h5_f:

            dims = [write_utils.Dimension('Freq', 'Hz', np.linspace(300, 350, 5)),
                    write_utils.Dimension('Bias', 'V', [-2, 4, 10]),
                    write_utils.Dimension('Cycle', 'a.u.', 2)]

            h5_spec_inds_orig, h5_spec_vals_orig = hdf_utils.write_ind_val_dsets(h5_f, dims, is_spectral=True)
            new_base_name = 'Blah'
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_f, h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig,
                                                                                   ['Freq', 'Bias'],
                                                                                   basename=new_base_name)

            dim_names = ['Cycle']
            dim_units = ['a.u.']
            ref_inds = np.expand_dims(np.arange(2), axis=0)
            ref_vals = np.expand_dims([0, 1], axis=0)
            for h5_dset, exp_dtype, exp_name, ref_data in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                              [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                              [new_base_name + '_Indices', new_base_name + '_Values'],
                                                              [ref_inds, ref_vals]):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_spec_inds_orig.parent)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_write_reduced_anc_dsets_3d_to_1d_spec_slowest(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)

        with h5py.File(duplicate_path) as h5_f:

            dims = [write_utils.Dimension('Freq', 'Hz', np.linspace(300, 350, 5)),
                    write_utils.Dimension('Bias', 'V', [-2, 4, 10]),
                    write_utils.Dimension('Cycle', 'a.u.', 2)]

            h5_spec_inds_orig, h5_spec_vals_orig = hdf_utils.write_ind_val_dsets(h5_f, dims, is_spectral=True)
            new_base_name = 'Blah'
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_f, h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig,
                                                                                   ['Cycle', 'Bias'],
                                                                                   basename=new_base_name)

            dim_names = ['Freq']
            dim_units = ['Hz']
            ref_inds = np.expand_dims(np.arange(5), axis=0)
            ref_vals = np.expand_dims(np.linspace(300, 350, 5), axis=0)
            for h5_dset, exp_dtype, exp_name, ref_data in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                              [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                              [new_base_name + '_Indices', new_base_name + '_Values'],
                                                              [ref_inds, ref_vals]):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_spec_inds_orig.parent)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_write_reduced_anc_dsets_3d_to_2d_spec_fastest_n_slowest(self):
        duplicate_path = 'copy_test_hdf_utils.h5'
        data_utils.delete_existing_file(duplicate_path)

        with h5py.File(duplicate_path) as h5_f:

            dims = [write_utils.Dimension('Freq', 'Hz', np.linspace(300, 350, 5)),
                    write_utils.Dimension('Bias', 'V', [-2, 4, 10]),
                    write_utils.Dimension('Cycle', 'a.u.', 2)]

            h5_spec_inds_orig, h5_spec_vals_orig = hdf_utils.write_ind_val_dsets(h5_f, dims, is_spectral=True)
            new_base_name = 'Blah'
            h5_spec_inds_new, h5_spec_vals_new = hdf_utils.write_reduced_anc_dsets(h5_f, h5_spec_inds_orig,
                                                                                   h5_spec_vals_orig,
                                                                                   ['Bias'],
                                                                                   basename=new_base_name)

            dim_names = ['Freq', 'Cycle']
            dim_units = ['Hz', 'a.u.']
            ref_vals = np.vstack((np.tile(np.linspace(300, 350, 5), 2),
                                  np.repeat(np.arange(2), 5)))
            ref_inds = np.vstack((np.tile(np.arange(5, dtype=np.uint16), 2),
                                  np.repeat(np.arange(2, dtype=np.uint16), 5)))
            for h5_dset, exp_dtype, exp_name, ref_data in zip([h5_spec_inds_new, h5_spec_vals_new],
                                                              [h5_spec_inds_orig.dtype, h5_spec_vals_orig.dtype],
                                                              [new_base_name + '_Indices', new_base_name + '_Values'],
                                                              [ref_inds, ref_vals]):
                self.assertIsInstance(h5_dset, h5py.Dataset)
                self.assertEqual(h5_dset.parent, h5_spec_inds_orig.parent)
                self.assertEqual(h5_dset.name.split('/')[-1], exp_name)
                self.assertTrue(np.allclose(ref_data, h5_dset[()]))
                self.assertEqual(h5_dset.dtype, exp_dtype)
                self.assertTrue(np.all([_ in h5_dset.attrs.keys() for _ in ['labels', 'units']]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_names, hdf_utils.get_attr(h5_dset, 'labels'))]))
                self.assertTrue(np.all([x == y for x, y in zip(dim_units, hdf_utils.get_attr(h5_dset, 'units'))]))
                # assert region references
                for dim_ind, curr_name in enumerate(dim_names):
                    self.assertTrue(np.allclose(np.squeeze(ref_data[dim_ind]),
                                                np.squeeze(h5_dset[h5_dset.attrs[curr_name]])))

        os.remove(duplicate_path)

    def test_find_dataset_legal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_group = h5_f['/Raw_Measurement/']
            with self.assertRaises(TypeError):
                ret_val = hdf_utils.find_dataset(h5_group, np.arange(4))

    def test_find_dataset_invalid_type_dset(self):
        with self.assertRaises(TypeError):
            _ = hdf_utils.find_dataset(4.324, 'Spectroscopic_Indices')

    def test_find_dataset_illegal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_group = h5_f['/Raw_Measurement/']
            ret_val = hdf_utils.find_dataset(h5_group, 'Does_Not_Exist')
            self.assertEqual(len(ret_val), 0)

    def test_find_results_groups_legal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            expected_groups = [h5_f['/Raw_Measurement/source_main-Fitter_000'],
                               h5_f['/Raw_Measurement/source_main-Fitter_001']]
            ret_val = hdf_utils.find_results_groups(h5_main, 'Fitter')
            self.assertEqual(set(ret_val), set(expected_groups))

    def test_find_results_groups_no_dset(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            with self.assertRaises(TypeError):
                _ = hdf_utils.find_results_groups(h5_f, 'Fitter')

    def test_find_results_groups_not_string(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            with self.assertRaises(TypeError):
                _ = hdf_utils.find_results_groups(h5_main, np.arange(5))

    def test_find_results_groups_illegal(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            ret_val = hdf_utils.find_results_groups(h5_main, 'Blah')
            self.assertEqual(len(ret_val), 0)

    def test_check_for_matching_attrs_dset_no_attrs(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            self.assertTrue(hdf_utils.check_for_matching_attrs(h5_main, new_parms=None))

    def test_check_for_matching_attrs_dset_matching_attrs(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'units': 'A', 'quantity':'Current'}
            self.assertTrue(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_matching_attrs_dset_one_mismatched_attrs(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'units': 'A', 'blah': 'meh'}
            self.assertFalse(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_matching_attrs_grp(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main-Fitter_000']
            attrs = {'att_1': 'string_val', 'att_2': 1.2345,
                     'att_3': [1, 2, 3, 4], 'att_4': ['str_1', 'str_2', 'str_3']}
            self.assertTrue(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_matching_attrs_grp_mismatched_types_01(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main-Fitter_000']
            attrs = {'att_4': 'string_val'}
            self.assertFalse(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_matching_attrs_grp_mismatched_types_02(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main-Fitter_000']
            attrs = {'att_1': ['str_1', 'str_2', 'str_3']}
            self.assertFalse(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_matching_attrs_grp_mismatched_types_03(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main-Fitter_000']
            attrs = {'att_4': [1, 4.234, 'str_3']}
            self.assertFalse(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_matching_attrs_grp_mismatched_types_04(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main-Fitter_000']
            attrs = {'att_4': [1, 4.234, 45]}
            self.assertFalse(hdf_utils.check_for_matching_attrs(h5_main, new_parms=attrs))

    def test_check_for_old_exact_match(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'att_1': 'string_val', 'att_2': 1.2345,
                     'att_3': [1, 2, 3, 4], 'att_4': ['str_1', 'str_2', 'str_3']}
            [h5_ret_grp] = hdf_utils.check_for_old(h5_main, 'Fitter', new_parms=attrs, target_dset=None)
            self.assertEqual(h5_ret_grp, h5_f['/Raw_Measurement/source_main-Fitter_000'])

    def test_check_for_old_subset_but_match(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'att_2': 1.2345,
                     'att_3': [1, 2, 3, 4], 'att_4': ['str_1', 'str_2', 'str_3']}
            [h5_ret_grp] = hdf_utils.check_for_old(h5_main, 'Fitter', new_parms=attrs, target_dset=None)
            self.assertEqual(h5_ret_grp, h5_f['/Raw_Measurement/source_main-Fitter_000'])

    def test_check_for_old_exact_match_02(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'att_1': 'other_string_val', 'att_2': 5.4321,
                     'att_3': [4, 1, 3], 'att_4': ['s', 'str_2', 'str_3']}
            [h5_ret_grp] = hdf_utils.check_for_old(h5_main, 'Fitter', new_parms=attrs, target_dset=None)
            self.assertEqual(h5_ret_grp, h5_f['/Raw_Measurement/source_main-Fitter_001'])

    def test_check_for_old_fail_01(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'att_1': [4, 1, 3], 'att_2': ['s', 'str_2', 'str_3'],
                     'att_3': 'other_string_val', 'att_4': 5.4321}
            ret_val = hdf_utils.check_for_old(h5_main, 'Fitter', new_parms=attrs, target_dset=None)
            self.assertIsInstance(ret_val, list)
            self.assertEqual(len(ret_val), 0)

    def test_check_for_old_fail_02(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            attrs = {'att_x': [4, 1, 3], 'att_z': ['s', 'str_2', 'str_3'],
                     'att_y': 'other_string_val', 'att_4': 5.4321}
            ret_val = hdf_utils.check_for_old(h5_main, 'Fitter', new_parms=attrs, target_dset=None)
            self.assertIsInstance(ret_val, list)
            self.assertEqual(len(ret_val), 0)

    def test_create_index_group_first_group(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_group = hdf_utils.create_indexed_group(h5_f, 'Hello')
            self.assertIsInstance(h5_group, h5py.Group)
            self.assertEqual(h5_group.name, '/Hello_000')
            self.assertEqual(h5_group.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_group)

            h5_sub_group = hdf_utils.create_indexed_group(h5_group, 'Test')
            self.assertIsInstance(h5_sub_group, h5py.Group)
            self.assertEqual(h5_sub_group.name, '/Hello_000/Test_000')
            self.assertEqual(h5_sub_group.parent, h5_group)
            data_utils.verify_book_keeping_attrs(self,  h5_sub_group)
        os.remove(file_path)

    def test_create_index_group_second(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_group_1 = hdf_utils.create_indexed_group(h5_f, 'Hello')
            self.assertIsInstance(h5_group_1, h5py.Group)
            self.assertEqual(h5_group_1.name, '/Hello_000')
            self.assertEqual(h5_group_1.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_group_1)

            h5_group_2 = hdf_utils.create_indexed_group(h5_f, 'Hello')
            self.assertIsInstance(h5_group_2, h5py.Group)
            self.assertEqual(h5_group_2.name, '/Hello_001')
            self.assertEqual(h5_group_2.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_group_2)
        os.remove(file_path)

    def test_create_index_group_w_suffix_(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_group = hdf_utils.create_indexed_group(h5_f, 'Hello_')
            self.assertIsInstance(h5_group, h5py.Group)
            self.assertEqual(h5_group.name, '/Hello_000')
            self.assertEqual(h5_group.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_group)
        os.remove(file_path)

    def test_create_index_group_empty_base_name(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            with self.assertRaises(ValueError):
                _ = hdf_utils.create_indexed_group(h5_f, '    ')

        os.remove(file_path)

    def test_create_results_group_first(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset = h5_f.create_dataset('Main', data=[1, 2, 3])
            h5_group = hdf_utils.create_results_group(h5_dset, 'Tool')
            self.assertIsInstance(h5_group, h5py.Group)
            self.assertEqual(h5_group.name, '/Main-Tool_000')
            self.assertEqual(h5_group.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_group)

            h5_dset = h5_group.create_dataset('Main_Dataset', data=[1, 2, 3])
            h5_sub_group = hdf_utils.create_results_group(h5_dset, 'SHO_Fit')
            self.assertIsInstance(h5_sub_group, h5py.Group)
            self.assertEqual(h5_sub_group.name, '/Main-Tool_000/Main_Dataset-SHO_Fit_000')
            self.assertEqual(h5_sub_group.parent, h5_group)
            data_utils.verify_book_keeping_attrs(self,  h5_sub_group)
        os.remove(file_path)

    def test_create_results_group_second(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset = h5_f.create_dataset('Main', data=[1, 2, 3])
            h5_group = hdf_utils.create_results_group(h5_dset, 'Tool')
            self.assertIsInstance(h5_group, h5py.Group)
            self.assertEqual(h5_group.name, '/Main-Tool_000')
            self.assertEqual(h5_group.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_group)

            h5_sub_group = hdf_utils.create_results_group(h5_dset, 'Tool')
            self.assertIsInstance(h5_sub_group, h5py.Group)
            self.assertEqual(h5_sub_group.name, '/Main-Tool_001')
            self.assertEqual(h5_sub_group.parent, h5_f)
            data_utils.verify_book_keeping_attrs(self,  h5_sub_group)
        os.remove(file_path)

    def test_create_results_group_empty_tool_name(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset = h5_f.create_dataset('Main', data=[1, 2, 3])
            with self.assertRaises(ValueError):
                _ = hdf_utils.create_results_group(h5_dset, '   ')
        os.remove(file_path)

    def test_create_results_group_not_dataset(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            with self.assertRaises(TypeError):
                _ = hdf_utils.create_results_group(h5_f, 'Tool')

        os.remove(file_path)

    def test_assign_group_index_existing(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_group = h5_f['/Raw_Measurement']
            ret_val = hdf_utils.assign_group_index(h5_group, 'source_main-Fitter')
            self.assertEqual(ret_val, 'source_main-Fitter_002')

    def test_assign_group_index_new(self):
        with h5py.File(data_utils.std_beps_path, mode='r') as h5_f:
            h5_group = h5_f['/Raw_Measurement']
            ret_val = hdf_utils.assign_group_index(h5_group, 'blah_')
            self.assertEqual(ret_val, 'blah_000')

    def test_link_as_main(self):
        file_path = 'link_as_main.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_raw_grp = h5_f.create_group('Raw_Measurement')

            num_rows = 3
            num_cols = 5
            num_cycles = 2
            num_cycle_pts = 7

            source_dset_name = 'source_main'

            source_pos_data = np.vstack((np.tile(np.arange(num_cols), num_rows),
                                         np.repeat(np.arange(num_rows), num_cols))).T
            pos_attrs = {'units': ['nm', 'um'], 'labels': ['X', 'Y']}

            h5_pos_inds = h5_raw_grp.create_dataset('Position_Indices', data=source_pos_data, dtype=np.uint16)
            data_utils.write_aux_reg_ref(h5_pos_inds, pos_attrs['labels'], is_spec=False)
            data_utils.write_string_list_as_attr(h5_pos_inds, pos_attrs)

            h5_pos_vals = h5_raw_grp.create_dataset('Position_Values', data=source_pos_data, dtype=np.float32)
            data_utils.write_aux_reg_ref(h5_pos_vals, pos_attrs['labels'], is_spec=False)
            data_utils.write_string_list_as_attr(h5_pos_vals, pos_attrs)

            source_spec_data = np.vstack((np.tile(np.arange(num_cycle_pts), num_cycles),
                                          np.repeat(np.arange(num_cycles), num_cycle_pts)))
            source_spec_attrs = {'units': ['V', ''], 'labels': ['Bias', 'Cycle']}

            h5_source_spec_inds = h5_raw_grp.create_dataset('Spectroscopic_Indices', data=source_spec_data,
                                                            dtype=np.uint16)
            data_utils.write_aux_reg_ref(h5_source_spec_inds, source_spec_attrs['labels'], is_spec=True)
            data_utils.write_string_list_as_attr(h5_source_spec_inds, source_spec_attrs)

            h5_source_spec_vals = h5_raw_grp.create_dataset('Spectroscopic_Values', data=source_spec_data,
                                                            dtype=np.float32)
            data_utils.write_aux_reg_ref(h5_source_spec_vals, source_spec_attrs['labels'], is_spec=True)
            data_utils.write_string_list_as_attr(h5_source_spec_vals, source_spec_attrs)

            source_main_data = np.random.rand(num_rows * num_cols, num_cycle_pts * num_cycles)
            h5_source_main = h5_raw_grp.create_dataset(source_dset_name, data=source_main_data)
            data_utils.write_safe_attrs(h5_source_main, {'units': 'A', 'quantity': 'Current'})

            self.assertFalse(hdf_utils.check_if_main(h5_source_main))

            # Now need to link as main!
            hdf_utils.link_as_main(h5_source_main, h5_pos_inds, h5_pos_vals, h5_source_spec_inds, h5_source_spec_vals)

            # Finally:
            self.assertTrue(hdf_utils.check_if_main(h5_source_main))

        os.remove(file_path)

    def test_link_as_main_size_mismatch(self):
        file_path = 'link_as_main.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_raw_grp = h5_f.create_group('Raw_Measurement')

            num_rows = 3
            num_cols = 5
            num_cycles = 2
            num_cycle_pts = 7

            source_dset_name = 'source_main'

            source_pos_data = np.vstack((np.tile(np.arange(num_cols), num_rows),
                                         np.repeat(np.arange(num_rows), num_cols))).T
            pos_attrs = {'units': ['nm', 'um'], 'labels': ['X', 'Y']}

            h5_pos_inds = h5_raw_grp.create_dataset('Position_Indices', data=source_pos_data, dtype=np.uint16)
            data_utils.write_aux_reg_ref(h5_pos_inds, pos_attrs['labels'], is_spec=False)
            data_utils.write_string_list_as_attr(h5_pos_inds, pos_attrs)

            h5_pos_vals = h5_raw_grp.create_dataset('Position_Values', data=source_pos_data, dtype=np.float32)
            data_utils.write_aux_reg_ref(h5_pos_vals, pos_attrs['labels'], is_spec=False)
            data_utils.write_string_list_as_attr(h5_pos_vals, pos_attrs)

            source_spec_data = np.vstack((np.tile(np.arange(num_cycle_pts), num_cycles),
                                          np.repeat(np.arange(num_cycles), num_cycle_pts)))
            source_spec_attrs = {'units': ['V', ''], 'labels': ['Bias', 'Cycle']}

            h5_source_spec_inds = h5_raw_grp.create_dataset('Spectroscopic_Indices', data=source_spec_data,
                                                            dtype=np.uint16)
            data_utils.write_aux_reg_ref(h5_source_spec_inds, source_spec_attrs['labels'], is_spec=True)
            data_utils.write_string_list_as_attr(h5_source_spec_inds, source_spec_attrs)

            h5_source_spec_vals = h5_raw_grp.create_dataset('Spectroscopic_Values', data=source_spec_data,
                                                            dtype=np.float32)
            data_utils.write_aux_reg_ref(h5_source_spec_vals, source_spec_attrs['labels'], is_spec=True)
            data_utils.write_string_list_as_attr(h5_source_spec_vals, source_spec_attrs)

            source_main_data = np.random.rand(num_rows * num_cols, num_cycle_pts * num_cycles)
            h5_source_main = h5_raw_grp.create_dataset(source_dset_name, data=source_main_data)
            data_utils.write_safe_attrs(h5_source_main, {'units': 'A', 'quantity': 'Current'})

            self.assertFalse(hdf_utils.check_if_main(h5_source_main))

            # Swap the order of the datasets to cause a clash in the shapes
            with self.assertRaises(ValueError):
                hdf_utils.link_as_main(h5_source_main, h5_source_spec_inds, h5_pos_vals, h5_pos_inds,
                                       h5_source_spec_vals)

        os.remove(file_path)

    def test_copy_attributes_file_dset(self):
        file_path = 'test.h5'
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        also_easy_attr = {'N_numbers': [1, -53.6, 0.000463]}
        hard_attrs = {'N_strings': np.array(['a', 'bc', 'def'], dtype='S')}
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_f.attrs.update(easy_attrs)
            h5_f.attrs.update(also_easy_attr)
            h5_f.attrs.update(hard_attrs)
            h5_dset = h5_f.create_dataset('Main_01', data=[1, 2, 3])
            hdf_utils.copy_attributes(h5_f, h5_dset)
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_dset.attrs[key])
            for key, val in also_easy_attr.items():
                self.assertTrue(np.all([x == y for x, y in zip(val, h5_dset.attrs[key])]))
            for key, val in hard_attrs.items():
                self.assertTrue(np.all([x == y for x, y in zip(val, h5_dset.attrs[key])]))
        os.remove(file_path)

    def test_copy_attributes_group_dset(self):
        file_path = 'test.h5'
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        also_easy_attr = {'N_numbers': [1, -53.6, 0.000463]}
        hard_attrs = {'N_strings': np.array(['a', 'bc', 'def'], dtype='S')}
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_group = h5_f.create_group('Group')
            h5_group.attrs.update(easy_attrs)
            h5_group.attrs.update(also_easy_attr)
            h5_group.attrs.update(hard_attrs)
            h5_dset = h5_f.create_dataset('Main_01', data=[1, 2, 3])
            hdf_utils.copy_attributes(h5_group, h5_dset)
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_dset.attrs[key])
            for key, val in also_easy_attr.items():
                self.assertTrue(np.all([x == y for x, y in zip(val, h5_dset.attrs[key])]))
            for key, val in hard_attrs.items():
                self.assertTrue(np.all([x == y for x, y in zip(val, h5_dset.attrs[key])]))
        os.remove(file_path)

    def test_copy_attributes_dset_w_reg_ref_group_but_skipped(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        data = np.random.rand(5, 7)
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=data)
            h5_dset_source.attrs.update(easy_attrs)
            h5_dset_sink = h5_f.create_dataset('Sink', data=data)
            reg_refs = {'even_rows': (slice(0, None, 2), slice(None)),
                        'odd_rows': (slice(1, None, 2), slice(None))}
            for reg_ref_name, reg_ref_tuple in reg_refs.items():
                h5_dset_source.attrs[reg_ref_name] = h5_dset_source.regionref[reg_ref_tuple]

            hdf_utils.copy_attributes(h5_dset_source, h5_dset_sink, skip_refs=True)

            self.assertEqual(len(h5_dset_sink.attrs), len(easy_attrs))
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_dset_sink.attrs[key])

        os.remove(file_path)

    def test_copy_attributes_dset_w_reg_ref_group_to_file(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        data = np.random.rand(5, 7)
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=data)
            h5_dset_source.attrs.update(easy_attrs)
            reg_refs = {'even_rows': (slice(None), slice(0, None, 2)),
                        'odd_rows': (slice(None), slice(1, None, 2))}
            for reg_ref_name, reg_ref_tuple in reg_refs.items():
                h5_dset_source.attrs[reg_ref_name] = h5_dset_source.regionref[reg_ref_tuple]

            if sys.version_info.major == 3:
                with self.assertWarns(UserWarning):
                    hdf_utils.copy_attributes(h5_dset_source, h5_f, skip_refs=False)
            else:
                hdf_utils.copy_attributes(h5_dset_source, h5_f, skip_refs=False)

            self.assertEqual(len(h5_f.attrs), len(easy_attrs))
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_f.attrs[key])

        os.remove(file_path)

    def test_copy_attributes_dset_w_reg_ref_group(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        data = np.random.rand(5, 7)
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=data)
            h5_dset_source.attrs.update(easy_attrs)
            h5_dset_sink = h5_f.create_dataset('Sink', data=data)
            reg_refs = {'even_rows': (slice(0, None, 2), slice(None)),
                        'odd_rows': (slice(1, None, 2), slice(None))}
            for reg_ref_name, reg_ref_tuple in reg_refs.items():
                h5_dset_source.attrs[reg_ref_name] = h5_dset_source.regionref[reg_ref_tuple]

            hdf_utils.copy_attributes(h5_dset_source, h5_dset_sink, skip_refs=False)

            self.assertEqual(len(h5_dset_sink.attrs), len(reg_refs) + len(easy_attrs))
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_dset_sink.attrs[key])

            self.assertTrue('labels' not in h5_dset_sink.attrs.keys())

            expected_data = [data[0:None:2, :], data[1:None:2, :]]
            written_data = [h5_dset_sink[h5_dset_sink.attrs['even_rows']],
                            h5_dset_sink[h5_dset_sink.attrs['odd_rows']]]

            for exp, act in zip(expected_data, written_data):
                self.assertTrue(np.allclose(exp, act))

        os.remove(file_path)

    def test_copy_attributes_illegal_to_from_reg_ref(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        data = np.random.rand(5, 7)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=data)
            h5_dset_dest = h5_f.create_dataset('Sink', data=data[:-1, :-1])
            reg_refs = {'even_rows': (slice(0, None, 2), slice(None)),
                        'odd_rows': (slice(1, None, 2), slice(None))}
            for reg_ref_name, reg_ref_tuple in reg_refs.items():
                h5_dset_source.attrs[reg_ref_name] = h5_dset_source.regionref[reg_ref_tuple]

            if sys.version_info.major == 3:
                with self.assertWarns(UserWarning):
                    hdf_utils.copy_attributes(h5_dset_source, h5_dset_dest, skip_refs=False)
            else:
                hdf_utils.copy_attributes(h5_dset_source, h5_dset_dest, skip_refs=False)

    def test_copy_main_attributes_valid(self):
        file_path = 'test.h5'
        main_attrs = {'quantity': 'Current', 'units': 'nA'}
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Main_01', data=[1, 23])
            h5_dset_source.attrs.update(main_attrs)
            h5_group = h5_f.create_group('Group')
            h5_dset_sink = h5_group.create_dataset('Main_02', data=[4, 5])
            hdf_utils.copy_main_attributes(h5_dset_source, h5_dset_sink)
            for key, val in main_attrs.items():
                self.assertEqual(val, h5_dset_sink.attrs[key])
        os.remove(file_path)

    def test_copy_main_attributes_no_main_attrs(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Main_01', data=[1, 23])
            h5_group = h5_f.create_group('Group')
            h5_dset_sink = h5_group.create_dataset('Main_02', data=[4, 5])
            with self.assertRaises(KeyError):
                hdf_utils.copy_main_attributes(h5_dset_source, h5_dset_sink)
        os.remove(file_path)

    def test_copy_main_attributes_wrong_objects(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Main_01', data=[1, 23])
            h5_group = h5_f.create_group('Group')
            with self.assertRaises(TypeError):
                hdf_utils.copy_main_attributes(h5_dset_source, h5_group)
            with self.assertRaises(TypeError):
                hdf_utils.copy_main_attributes(h5_group, h5_dset_source)
        os.remove(file_path)

    def test_create_empty_dataset_same_group_new_attrs(self):
        file_path = 'test.h5'
        existing_attrs = {'a': 1, 'b': 'Hello'}
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=[1, 2, 3])
            h5_dset_source.attrs.update(existing_attrs)
            h5_duplicate = hdf_utils.create_empty_dataset(h5_dset_source, np.float16, 'Duplicate', new_attrs=easy_attrs)
            self.assertIsInstance(h5_duplicate, h5py.Dataset)
            self.assertEqual(h5_duplicate.parent, h5_dset_source.parent)
            self.assertEqual(h5_duplicate.name, '/Duplicate')
            self.assertEqual(h5_duplicate.dtype, np.float16)
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_duplicate.attrs[key])
            for key, val in existing_attrs.items():
                self.assertEqual(val, h5_duplicate.attrs[key])

        os.remove(file_path)

    def test_create_empty_dataset_diff_groups(self):
        file_path = 'test.h5'
        existing_attrs = {'a': 1, 'b': 'Hello'}
        easy_attrs = {'1_string': 'Current', '1_number': 35.23}
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=[1, 2, 3])
            h5_dset_source.attrs.update(existing_attrs)
            h5_group = h5_f.create_group('Group')
            h5_duplicate = hdf_utils.create_empty_dataset(h5_dset_source, np.float16, 'Duplicate',
                                                          h5_group=h5_group, new_attrs=easy_attrs)
            self.assertIsInstance(h5_duplicate, h5py.Dataset)
            self.assertEqual(h5_duplicate.parent, h5_group)
            self.assertEqual(h5_duplicate.name, '/Group/Duplicate')
            self.assertEqual(h5_duplicate.dtype, np.float16)
            for key, val in easy_attrs.items():
                self.assertEqual(val, h5_duplicate.attrs[key])
            for key, val in existing_attrs.items():
                self.assertEqual(val, h5_duplicate.attrs[key])

        os.remove(file_path)

    def test_create_empty_dataset_w_region_refs(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        data = np.random.rand(5, 7)
        main_attrs = {'quantity': 'Current', 'units': 'nA'}
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=data)
            h5_dset_source.attrs.update(main_attrs)
            reg_refs = {'even_rows': (slice(0, None, 2), slice(None)),
                        'odd_rows': (slice(1, None, 2), slice(None))}

            for reg_ref_name, reg_ref_tuple in reg_refs.items():
                h5_dset_source.attrs[reg_ref_name] = h5_dset_source.regionref[reg_ref_tuple]

            h5_copy = hdf_utils.create_empty_dataset(h5_dset_source, np.float16, 'Existing')

            for reg_ref_name in reg_refs.keys():
                self.assertTrue(isinstance(h5_copy.attrs[reg_ref_name], h5py.RegionReference))
                self.assertTrue(h5_dset_source[h5_dset_source.attrs[reg_ref_name]].shape == h5_copy[
                    h5_copy.attrs[reg_ref_name]].shape)

        os.remove(file_path)

    def test_create_empty_dataset_existing_dset_name(self):
        file_path = 'test.h5'
        data_utils.delete_existing_file(file_path)
        with h5py.File(file_path) as h5_f:
            h5_dset_source = h5_f.create_dataset('Source', data=[1, 2, 3])
            _ = h5_f.create_dataset('Existing', data=[4, 5, 6])
            if sys.version_info.major == 3:
                with self.assertWarns(UserWarning):
                    h5_duplicate = hdf_utils.create_empty_dataset(h5_dset_source, np.float16, 'Existing')
            else:
                h5_duplicate = hdf_utils.create_empty_dataset(h5_dset_source, np.float16, 'Existing')
            self.assertIsInstance(h5_duplicate, h5py.Dataset)
            self.assertEqual(h5_duplicate.name, '/Existing')
            self.assertTrue(np.allclose(h5_duplicate[()], np.zeros(3)))
            self.assertEqual(h5_duplicate.dtype, np.float16)
        os.remove(file_path)

    def test_check_and_link_ancillary_not_dset(self):
        with self.assertRaises(TypeError):
            hdf_utils.check_and_link_ancillary(np.arange(5), ['Spec'])


if __name__ == '__main__':
    unittest.main()
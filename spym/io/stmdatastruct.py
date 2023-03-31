import xarray as xr
import pylab as pl
import numpy as np
import spym
## Using the old loader
from spym.io import rhksm4

class stmdata:
	"""
	stmData class as a container for the xarray based structure of the data
	Parameters:
	repetitions: the number of spectra in each physical position of the tip
	alternate: True if forward and backward bias sweeps are turned on, False if not
	"""
	def __init__(self, filename, repetitions = 1, alternate = True, datatype = 'map', **kwargs):
		# check if parameters passed to the class are valid
		if repetitions <= 0:
			print("repetitions needs to be an integer, with a value of 1 or above. Default is 1")
		elif isinstance(repetitions, int) == False:
			print("repetitions needs to be an integer. Default is 1")

		if isinstance(alternate, bool) == False:
			print("alternate needs to be a bool variable: True or False. Default is True")

		if (datatype != 'map') and (datatype != 'line') and (datatype != 'spec') and (datatype != 'image'):
			print('datatype must be either: map, line, spec or image')
			return


		self.filename = filename
		# number of spectra at a tip position
		self.repetitions = repetitions
		# Boolean value, True if alternate scan directions is turned on
		self.alternate = alternate
		self.datatype = datatype

		# Load the data using spym
		self.spymdata = load_spym(self.filename)
		# check software version. Not tested for MinorVer < 6
		l = list(self.spymdata.keys())
		if self.spymdata[l[-1]].attrs['RHK_MinorVer'] < 6:
			print('stmdatastruct not tested for RHK Rev version < 6. Some things might not work as expected.')

		# check type of data contained in the file
		self.datatype, self.spectype = checkdatatype(self)

		# if the file contains spectroscopy map
		if self.datatype == 'map':
			self = load_specmap(self)
		elif self.datatype == 'line':
			self = load_line(self)
		elif self.datatype == 'spec':
			self = load_spec(self)
		elif self.datatype == 'image':
			self = load_image(self)

	def print_info(self):
		for item in self.__dict__:
			print(item)
		print('\nspymdata:')
		for item in self.spymdata:
			print('\t', item)


def checkdatatype(stmdata_object):
	# Look at the metadata and structure of spectra coordinates to determine the type of file being worked with
	l = list(stmdata_object.spymdata.keys())
	if stmdata_object.spymdata[l[-1]].attrs['RHK_LineType'] == 7:
		stmdata_object.spectype = 'iv'
	elif stmdata_object.spymdata[l[-1]].attrs['RHK_LineType'] == 8:
		stmdata_object.spectype = 'iz'
	elif stmdata_object.spymdata[l[-1]].attrs['RHK_LineType'] == 0:
		stmdata_object.spectype = 'none'
	
	if stmdata_object.spymdata[l[-1]].attrs['RHK_PageType'] == 1:
		stmdata_object.datatype = 'image'
	elif stmdata_object.spymdata[l[-1]].attrs['RHK_PageType'] == 38:
		stmdata_object.datatype = 'spec'
	elif stmdata_object.spymdata[l[-1]].attrs['RHK_PageType'] == 16:
		# this can be either a line spectrum or a map
		# decide based on the aspect ratio of the spectroscopy tip positions
		xcoo = pl.array(stmdata_object.spymdata[l[-1]].attrs['RHK_SpecDrift_Xcoord'])
		ycoo = pl.array(stmdata_object.spymdata[l[-1]].attrs['RHK_SpecDrift_Ycoord'])
		if aspect_ratio(xcoo, ycoo) > 10:
			stmdata_object.datatype = 'line'
		else:
			stmdata_object.datatype = 'map'

	print(stmdata_object.datatype)
	print(stmdata_object.spectype)
	return stmdata_object.datatype, stmdata_object.spectype

def aspect_ratio(x, y):
    xy = np.stack((x, y), axis=0)
    eigvals, eigvecs = np.linalg.eig(np.cov(xy))
    center = xy.mean(axis=-1)
    for val, vec in zip(eigvals, eigvecs.T):
        val *= 2
        xcov,ycov = np.vstack((center + val * vec, center, center - val * vec)).T
    aspect = max(eigvals) / min(eigvals)
    return aspect


def load_specmap(stmdata_object):
	# total number of spectra in one postion of the tip
	stmdata_object.numberofspectra = (stmdata_object.alternate + 1)*stmdata_object.repetitions
	# create a DataSet, containing the LIA and Current maps, with appropriate position coordinates
	stmdata_object = xr_spec(stmdata_object)
	# rescale the dimensions to nice values
	stmdata_object = rescale_spec(stmdata_object)
	# add metadata to the xarray
	stmdata_object = add_metadata(stmdata_object)
	return stmdata_object

def load_line(stmdata_object):
	return stmdata_object

def load_spec(stmdata_object):
	return stmdata_object

def load_image(stmdata_object):
	return stmdata_object

def xr_spec(stmdata_object):
	"""
	Create a DataSet containing the Lok-In (LIA) and Current spectroscopy data
	Use the absolute values of the tip positions as coordinates

	In spym the spectroscopy data is loaded into an array,
	which has axis=0 the number of datapoints in the spectra
	and axis=1 the number of spectra in total.

	When rearranging, the number of repetitions within each tip position is assumed to be 1
	and alternate scan direction is assumed to be turned on.
	These options can be changed by the parameters, `repetitions` and `alternate`
	"""

	# extract the numpy array containing the LIA data from the spym object
	specarray = stmdata_object.spymdata.LIA_Current.data
	# extract the numpy array containing the Current data from the spym object
	currentarray = stmdata_object.spymdata.Current.data

	# total number of spectra in one postion of the tip
	numberofspectra = (stmdata_object.alternate + 1)*stmdata_object.repetitions
	# size of the map in mapsize x mapsize
	mapsize = int(pl.sqrt(specarray.shape[1] / numberofspectra))

	# reshape LIA data
	# collect all spectra measured in the same `X, Y` coordinate into an axis (last) of an array.
	temp = pl.reshape(specarray, (specarray.shape[0], -1, numberofspectra), order='C')
	# Every other spectrum is a forward and backward scan in bias sweep. Separate the forward and backward scans into differing arrays by slicing.
	# These are all the forward and backward bias sweep spectra, arranged along axis=1, with axis=2 being the repetitions
	spec_fw = temp[:, :, 0::2]
	spec_bw = temp[:, :, 1::2]
	# reshape the forward and backward parts into a map
	speccmap_fw = pl.reshape(spec_fw, (spec_fw.shape[0], mapsize, mapsize, spec_fw.shape[2]), order='C')
	speccmap_bw = pl.reshape(spec_bw, (spec_bw.shape[0], mapsize, mapsize, spec_bw.shape[2]), order='C')
	"""
	The last axis (in this case with length of 1) contains the repeated scans in one particular pixel.
	If the `repetitions` variable is set to greater than 1, this will contains the repeated spectra within an `X, Y` pixel.
	The array needs to be flipped along axis = 1 (the "x" axis in the topography image) to fit with the data read by the ASCII method
	"""
	liafw = pl.flip(speccmap_fw, axis=1)
	liabw = pl.flip(speccmap_bw, axis=1)

	# reshape Current data
	temp = pl.reshape(currentarray, (currentarray.shape[0], -1, numberofspectra), order='C')
	# Every other spectrum is a forward and backward scan in bias sweep. Separate the forward and backward scans into differing arrays by slicing.
	# These are all the forward and backward bias sweep spectra, arranged along axis=1, with axis=2 being the repetitions
	current_fw = temp[:, :, 0::2]
	current_bw = temp[:, :, 1::2]
	# reshape the forward and backward parts into a map
	currentmap_fw = pl.reshape(current_fw, (current_fw.shape[0], mapsize, mapsize, current_fw.shape[2]), order='C')
	currentmap_bw = pl.reshape(current_bw, (current_bw.shape[0], mapsize, mapsize, current_bw.shape[2]), order='C')
	"""
	The last axis (in this case with length of 1) contains the repeated scans in one particular pixel.
	If the `repetitions` variable is set to greater than 1, this will contains the repeated spectra within an `X, Y` pixel.
	The array needs to be flipped along axis = 1 (the "x" axis in the topography image) to fit with the data read by the ASCII method
	"""
	currentfw = pl.flip(currentmap_fw, axis=1)
	currentbw = pl.flip(currentmap_bw, axis=1)	

	"""
	Coordinates of the spectroscopy map
	"""
	# 'RHK_SpecDrift_Xcoord' are the coordinates of the spectra.
	# This contains the coordinates in the order that the spectra are in. 
	xcoo = pl.array(stmdata_object.spymdata.LIA_Current.attrs['RHK_SpecDrift_Xcoord'])
	ycoo = pl.array(stmdata_object.spymdata.LIA_Current.attrs['RHK_SpecDrift_Ycoord'])
	# reshaping the coordinates similarly to the spectra. This is a coordinates mesh
	# at the end slicing the arrays to get the X, Y coordinates, we don't need the mesh
	tempx = pl.reshape(xcoo, (mapsize, mapsize, numberofspectra), order='C')[0, :, 0]
	tempy = pl.reshape(ycoo, (mapsize, mapsize, numberofspectra), order='C')[:, 0, 0]

	"""
	Constructing the xarray DataSet 
	"""
	# stacking the forward and backward bias sweeps and using the scandir coordinate
	# also adding specific attributes
	xrspec = xr.Dataset(
		data_vars = dict(
			lia = (['bias', 'specpos_x', 'specpos_y', 'repetitions', 'biasscandir'], pl.stack((liafw, liabw), axis=-1)),
			current = (['bias', 'specpos_x', 'specpos_y', 'repetitions', 'biasscandir'], pl.stack((currentfw, currentbw), axis=-1))
			),
		coords = dict(
			bias = stmdata_object.spymdata.coords['LIA_Current_x'].data,
			specpos_x = tempx,
			specpos_y = tempy,
			repetitions = pl.array(range(stmdata_object.repetitions)),
			biasscandir = pl.array(['left', 'right'], dtype = 'U')
			),
		attrs = dict(filename = stmdata_object.filename)
	)

	stmdata_object.specmap = xrspec
	return stmdata_object


def rescale_spec(stmdata_object):
	"""
	rescale the xarray Dataset
	rescale the data to nice values, nm for distances, pA for current and LIA
	"""
	# convert meters to nm
	stmdata_object.specmap.coords['specpos_x'] = stmdata_object.specmap.coords['specpos_x']*10**9
	stmdata_object.specmap.coords['specpos_y'] = stmdata_object.specmap.coords['specpos_y']*10**9
	# convert A to pA
	stmdata_object.specmap['lia'].data = stmdata_object.specmap['lia'].data*10**12
	stmdata_object.specmap['current'].data = stmdata_object.specmap['current'].data*10**12
	stmdata_object.specmap['lia'].attrs['units'] = 'pA'
	stmdata_object.specmap['lia'].attrs['long units'] = 'picoampere'
	stmdata_object.specmap['current'].attrs['units'] = 'pA'
	stmdata_object.specmap['current'].attrs['long units'] = 'picoampere'
	stmdata_object.specmap.coords['specpos_x'].attrs['units'] = 'nm'
	stmdata_object.specmap.coords['specpos_y'].attrs['units'] = 'nm'
	stmdata_object.specmap.coords['specpos_x'].attrs['long units'] = 'nanometer'
	stmdata_object.specmap.coords['specpos_y'].attrs['long units'] = 'nanometer'

	return stmdata_object


def add_metadata(stmdata_object):
	stmdata_object.specmap['lia'].attrs['bias'] = stmdata_object.spymdata.LIA_Current.attrs['bias']
	stmdata_object.specmap['current'].attrs['bias'] = stmdata_object.spymdata.Current.attrs['bias']

	stmdata_object.specmap.coords['bias'].attrs['units'] = 'V'
	stmdata_object.specmap.coords['bias'].attrs['long units'] = 'volt'
	stmdata_object.specmap['lia'].attrs['bias units'] = 'V'
	stmdata_object.specmap['current'].attrs['bias units'] = 'V'

	stmdata_object.specmap['lia'].attrs['setpoint'] = stmdata_object.spymdata.LIA_Current.attrs['RHK_Current']*10**12
	stmdata_object.specmap['current'].attrs['setpoint'] = stmdata_object.spymdata.Current.attrs['RHK_Current']*10**12

	stmdata_object.specmap['lia'].attrs['setpoint units'] = 'pA'
	stmdata_object.specmap['current'].attrs['setpoint units'] = 'pA'

	stmdata_object.specmap.attrs['measurement date'] = stmdata_object.spymdata.Current.attrs['RHK_Date']
	stmdata_object.specmap.attrs['measurement time'] = stmdata_object.spymdata.Current.attrs['RHK_Time']

	stmdata_object.specmap['lia'].attrs['time_per_point'] = stmdata_object.spymdata.LIA_Current.attrs['time_per_point']
	stmdata_object.specmap['current'].attrs['time_per_point'] = stmdata_object.spymdata.Current.attrs['time_per_point']

	return stmdata_object

"""Using spym to load the data from the sm4 file"""
def load_rhksm4(filename):
	"""Load the data from the .sm4 file using the old loader"""
	return rhksm4.load(filename)

def load_spym(filename):
	"""Load the data from the .sm4 file using spym"""
	return spym.load(filename)


#Imports 
import numpy as np 
from matplotlib import pyplot as plt 
from astropy import units as u 
from astropy import table
from astropy.table import hstack
from astropy.coordinates import SkyCoord

#load in catalogs 
dir_in = '/Users/yokisalcedo/Desktop/Emission-Line-Galaxy-Target-Selection/data/'   
dir_out = '/Users/yokisalcedo/Desktop/Emission-Line-Galaxy-Target-Selection/' # the directory where the output of this notebook will be stored
# Upload the main catalogue
hsc_cat = table.Table.read(dir_in+'HSC.fits',format='fits',hdu=1)

def flux_to_mag(flux):
    return -2.5*np.log10(flux*1e-9) + 8.90
# extinction corrected mags (extinction is negligible for XMM-LSS)
hsc_cat["i_mag"] = flux_to_mag(hsc_cat["i_cmodel_flux"])-hsc_cat["a_i"]
hsc_cat["r_mag"] = flux_to_mag(hsc_cat["r_cmodel_flux"])-hsc_cat["a_r"]
hsc_cat["z_mag"] = flux_to_mag(hsc_cat["z_cmodel_flux"])-hsc_cat["a_z"]
hsc_cat["g_mag"] = flux_to_mag(hsc_cat["g_cmodel_flux"])-hsc_cat["a_g"]
hsc_cat["y_mag"] = flux_to_mag(hsc_cat["y_cmodel_flux"])-hsc_cat["a_y"]
hsc_cat["i_fiber_mag"] = flux_to_mag(hsc_cat["i_fiber_flux"])-hsc_cat["a_i"]
hsc_cat["i_fiber_tot_mag"] = flux_to_mag(hsc_cat["i_fiber_tot_flux"])-hsc_cat["a_i"]
hsc_cat["g_fiber_mag"] = flux_to_mag(hsc_cat["g_fiber_flux"])-hsc_cat["a_g"]
hsc_cat["g_fiber_tot_mag"] = flux_to_mag(hsc_cat["g_fiber_tot_flux"])-hsc_cat["a_g"]
hsc_cat["r_fiber_mag"] = flux_to_mag(hsc_cat["r_fiber_flux"])-hsc_cat["a_r"]
hsc_cat["r_fiber_tot_mag"] = flux_to_mag(hsc_cat["r_fiber_tot_flux"])-hsc_cat["a_r"]
    
## Quality cuts
# valid I-band flux
mask = np.isfinite(hsc_cat["i_cmodel_flux"]) & (hsc_cat["i_cmodel_flux"]>0)
#cmodel fit not failed
mask &= (~hsc_cat["i_cmodel_flag"])
#General Failure Flag
mask &= (~hsc_cat["i_sdsscentroid_flag"])
mask &= np.isfinite(hsc_cat["g_cmodel_flux"]) & (hsc_cat["g_cmodel_flux"]>0)
#cmodel fit not failed
mask &= (~hsc_cat["g_cmodel_flag"])
#General Failure Flag
mask &= (~hsc_cat["g_sdsscentroid_flag"])
mask &= np.isfinite(hsc_cat["r_cmodel_flux"]) & (hsc_cat["r_cmodel_flux"]>0)
#cmodel fit not failed
mask &= (~hsc_cat["r_cmodel_flag"])
#General Failure Flag
mask &= (~hsc_cat["r_sdsscentroid_flag"])
mask &= np.isfinite(hsc_cat["y_cmodel_flux"]) & (hsc_cat["y_cmodel_flux"]>0)
#cmodel fit not failed
mask &= (~hsc_cat["y_cmodel_flag"])
#General Failure Flag
mask &= (~hsc_cat["y_sdsscentroid_flag"])
mask &= np.isfinite(hsc_cat["z_cmodel_flux"]) & (hsc_cat["z_cmodel_flux"]>0)
#cmodel fit not failed
mask &= (~hsc_cat["z_cmodel_flag"])
#General Failure Flag
mask &= (~hsc_cat["z_sdsscentroid_flag"])
hsc_cat = hsc_cat[mask]

#load in specz cataloges 
tert = table.Table.read('/Users/yokisalcedo/Desktop/Emission-Line-Galaxy-Target-Selection/data/all_elgs.fits',format='fits',hdu=1)
#cleaning specz catalog
elgmask = tert['TERTIARY_TARGET'] == 'ELG'
fiber_status = tert['COADD_FIBERSTATUS'] == 0 
exposure = tert['TSNR2_LRG']*12.15
tmask = exposure > 200
t_mask = np.logical_and.reduce((tmask, fiber_status, elgmask, tert['YSH']))
elgs = tert[t_mask]

#merge both hsc_cat and elgs catalogs, this combined catalog will be used to tweak the cuts and check our redshift distribution
ra_elg = elgs['TARGET_RA']
dec_elg = elgs['TARGET_DEC']
ra_hsc = hsc_cat['ra']
dec_hsc = hsc_cat['dec']
hsc_coord = SkyCoord(ra_hsc*u.degree, dec_hsc*u.degree)
elg_coord = SkyCoord(ra_elg*u.degree, dec_elg*u.degree)
idx_h, d2d_h, d3d_h = elg_coord.match_to_catalog_sky(hsc_coord)
dmask = d2d_h.arcsec < 0.000001
combined_cat = hstack([elgs, hsc_cat[idx_h]])[dmask]

#Masking with snr and chi2 cuts for combined_cat
o2_snr_comb = combined_cat['OII_FLUX']*np.sqrt(combined_cat['OII_FLUX_IVAR'])   
chi2_comb = combined_cat['DELTACHI2']
snr_mask_comb = o2_snr_comb > 10**(0.9 - 0.2*np.log10(chi2_comb))
snr_mask_comb = np.logical_or(snr_mask_comb, chi2_comb > 25)
snr_mask_comb_fail =~ snr_mask_comb

#Defining our specz and final cuts for our optimized sample
spectro_z = combined_cat['Z'][snr_mask_comb]
color_mask = np.logical_and((combined_cat['r_mag'][snr_mask_comb] - combined_cat['i_mag'][snr_mask_comb] < combined_cat['i_mag'][snr_mask_comb] - combined_cat['y_mag'][snr_mask_comb] - 0.19 ),
                             (combined_cat['i_mag'][snr_mask_comb] - combined_cat['y_mag'][snr_mask_comb] > 0.35 + 0.05636818841724967))
color_mask &= (combined_cat['i_mag'][snr_mask_comb] - combined_cat['z_mag'][snr_mask_comb]) > 0.37442580263398095
ccuts = np.logical_and(color_mask, combined_cat['g_fiber_mag'][snr_mask_comb] < 24.253228615646897) 

#load in the desi ELG distributions to plot against our final distribution
data = table.Table.read('/Users/yokisalcedo/Desktop/Emission-Line-Galaxy-Target-Selection/desi_elg_ts_zenodo/main-800coaddefftime1200-nz-zenodo.ecsv', format='ascii.ecsv')
data.colnames
zmin = data['ZMIN']
zmax = data['ZMAX']
lop_north = data['ELG_LOP_NORTH']
lop_south_decal = data['ELG_LOP_SOUTH_DECALS']
lop_south_des = data[ 'ELG_LOP_SOUTH_DES']
vlo_north = data['ELG_VLO_NORTH']
vlo_south_decal = data['ELG_VLO_SOUTH_DECALS']
vlo_south_des = data['ELG_VLO_SOUTH_DES']
lop_desi = data['ELG_LOP_DESI']
vlo_desi = data['ELG_VLO_DESI']
# - {AREA_NORTH: 4400}
# - {AREA_SOUTH_DECALS: 8500}
# - {AREA_SOUTH_DES: 1100}
weightedavg = (lop_north * 4400 + lop_south_decal * 8500 + lop_south_des * 1100 )/(14000)

'''Comparing our ELG's to DESI LOP ELG's '''
#normalize
values, edges = np.histogram(spectro_z[ccuts], bins = np.linspace(0,2,41))
wrongnorm = np.sum(values)
rightnorm = (1601.8044)
normhist = values * (rightnorm/wrongnorm)

#plot
fig, ax = plt.subplots()
ax.stairs(weightedavg, edges, linewidth = 2, color = 'grey', label = 'DESI LOP')
ax.stairs(normhist, edges, linewidth = 2, color = 'blue', label = "DESI-2 ELG's")
ax.axvline(x = 1.1,ls= '--', color='black')
ax.axvline(x = 1.60,ls= '--', color='black')
ax.xaxis.set_tick_params(labelsize = 12)
ax.yaxis.set_tick_params(labelsize = 12)
ax.set_xlabel('Spec z', fontsize = 16)
ax.set_ylabel('Observed N [$deg^{-2}$]', fontsize = 16)
ax.legend(loc = 'upper left', fontsize = 16)
plt.savefig('/Users/yokisalcedo/Desktop/Emission-Line-Galaxy-Target-Selection/script_figure/desi1_desi2_elgs.png', dpi = 300, bbox_inches='tight' )


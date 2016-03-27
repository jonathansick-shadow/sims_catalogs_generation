"""

ljones, jmyers

$Id$

MovingObject:
This is a class to hold individual MovingObject information, which is made up of the following info:
 - an orbit (cometary orbital elements q/e/i/node/argPeri/timePeri/epoch) 
     This is held in an associated (public) class, Orbit. A MovingObject contains one Orbit currently,
     but could be expanded in the future to hold orbits at multiple epochs.
 - multiple ephemerides (TAI|UTC-MJD/RA/Dec/VMag/dRA/dDec/Distance/dDistance/solar_elongation/magnitude..)
     This is also another associated (public) class, Ephemeris. A MovingObject contains a dictionary of 
     Ephemeris class objects. 
 - information on variability of the object, as well as its sedname 
      This is held in MovingObject itself, rather than the Orbit or Ephemeris classes.
MovingObject has some methods of its own: 
 - mjdTaiStr: because the Ephemeride dictionary is keyed from the mjd of the time of the ephemeris, there
 needs to be a way to replicate this key every time (floats are not guaranteed to evaluate to the same
 key value). So mjTaiStr takes a float mjd and returns a string which can be used for the key. 


 - calcEphemeris: this is a method on MovingObject because it requires knowing the orbit, but produces
 an Ephemeris object which is held within MovingObject.
 - getOrbArrayPyoorb: 
Orbit 
 and Ephemeris are classes holding the orbital information (and tasks on the orbit, such as conversions?)
and ephemeris information (and tasks on the ephemeris, such as calculation of the magnitude in a particular filter)

A class to be used in source catalog generation.  Holds an orbit/MJD (epoch for the orbit), a dictionary of ephemerides at various dates, as well as some bookkeeping about the object following said orbit.

"""

from DayMOPSObject import DayMOPSObject
import numpy as n
import pyoorb as oo


class MovingObject(DayMOPSObject):
    # DayMOPSObject provides automatic getters and setters based on "private" (_prefixed) variable names.

    def __init__(self, q, e, i, node, argPeri, timePeri, epoch, orb_timescale=3.0,
                 magHv=-99.9, phaseGv=0.15,
                 objtype=None, objid=None,
                 index=None, n_par=None, moid=None,
                 isVar=None, var_t0=None, var_timescale=None, var_fluxmax=None,
                 sedname = None,
                 u_opp=None, g_opp=None, r_opp=None, i_opp=None, z_opp=None, y_opp=None):
        """Init a MovingObject. Orbital parameters required, other information optional. 

        MovingObject contains an Orbit object, (potentially multiple) Ephemeris objects,
        and various bookkeeping pieces of information, such as the associated SED name."""
        # The only truly necessary part of class is orbital elements - set these, in Orbit object.
        self.Orbit = Orbit(q, e, i, node, argPeri, timePeri, epoch, orb_timescale)
        # Set up the ephemerides dictionary, which is currently empty.
        self.Ephemerides = {}
        # Set other values within the class.
        # Set values for identifying object ID and object type (objid & NEO/MBA, etc)
        self._objid = objid
        self._objtype = objtype
        # Set values for predicting magnitudes.
        self._magHv = magHv
        self._phaseGv = phaseGv
        # Set values for predicting magnitudes, if there is variability.
        self._isVar = isVar
        # var_t0 = the time of onset of variability.
        self._var_t0 = var_t0
        # var_timescale = period of variability.
        self._var_timescale = var_timescale
        # var_fluxnorm = max amplitude of the variability, in flux (relative to fluxNorm).
        self._var_fluxmax = var_fluxmax
        # sedname = the SED name
        self._sedname = sedname
        # The opposition values for ugrizy come from the database, as they are precalculated.
        self._u_opp = u_opp
        self._g_opp = g_opp
        self._r_opp = r_opp
        self._i_opp = i_opp
        self._z_opp = z_opp
        self._y_opp = y_opp
        # These are values that come from the orbit file, but are not currently used.
        self._index = index
        self._n_par = n_par
        self._moid = moid

    # Define methods that do work on MovingObject.
    def mjdTaiStr(self, mjdTai):
        """ Convert float/number mjdTai to string so can use for dictionary lookup.

        mjdTai should be a single floating point number, which is then returned as fixed-format string."""
        mjdstr = "%.8f" % (mjdTai)
        return mjdstr

    def getOrbArrayPyoorb(self, format='COM'):
        """Returns values of the orbital elements, in format suitable for use in ephemeris routines. """
        # This is a method on MovingObject rather than Orbit because it includes the magnitude and phase.
        # COM format is all that is currently needed or supported, but could be expanded in future.
        if format == 'COM':
            # Set up an array for pyoorb. The pyoorb array requires:
            # 0: orbitId
            # 1 - 6: orbital elements, using radians for angles
            # 7: element type code, where 2 = cometary - means timescale is TT, too
            # 8: epoch
            # 9: timescale for the epoch; 1= MJD_UTC, 2=UT1, 3=TT, 4=TAI
            # 10: H
            # 11: G
            orbitsArray = n.empty([1, 12], dtype=n.double, order='F')
            orbitsArray[0][:] = [self.getobjid(),
                                 self.Orbit.getq(),
                                 self.Orbit.gete(),
                                 n.radians(self.Orbit.geti()),
                                 n.radians(self.Orbit.getnode()),
                                 n.radians(self.Orbit.getargPeri()),
                                 self.Orbit.gettimePeri(),
                                 n.double(2),
                                 self.Orbit.getepoch(),
                                 self.Orbit.getorb_timescale(),
                                 self.getmagHv(),
                                 self.getphaseGv()]
            return orbitsArray
        else:
            # User requested format other than COM so we will currently return an exception.
            raise Exception('Only COM format orbital elements accepted')

    def calcEphemeris(self, mjdTaiList, obscode=807, eph_timescale=4.0):
        """ Calculate an ephemeris position for a single object at a list of times (or a single time).

        If calculating ephemerides for many objects, you should use the function in 
        MovingObjectList, as it should be faster. """
        # Convert float mjdTai's into strings for ephemeride dictionary lookup.
        mjdTaiListStr = []
        # Check if mjdTai is a list or not - if not, make into a list.
        if isinstance(mjdTaiList, list) == False:
            mjdTaiList = [mjdTaiList]
        for mjdTai in mjdTaiList:
            mjdTaiListStr.append(self.mjdTaiStr(mjdTai))
        # Get orbit in pyoorb array format.
        orbArray = self.getOrbArrayPyoorb()
        # Set up ephem_dates array for pyoorb.
        ephem_dates = n.zeros([len(mjdTaiList), 2], dtype=n.double, order='F')
        for i in range(len(mjdTaiList)):
            # The second element in dates is the units timescale of time ..
            # UTC/UT1/TT/TAI = 1/2/3/4.
            ephem_dates[i][:] = [mjdTaiList[i], eph_timescale]
        # Calculate the ephemerides with a call to pyoorb.
        # This assumes that somewhere you've set up pyoorb with a previous call to
        # oo.pyoorb.oorb_init(ephemeris_fname=ephem_datfile)
        ephems, err = oo.pyoorb.oorb_ephemeris(in_orbits = orbArray,
                                               in_obscode = obscode,
                                               in_date_ephems = ephem_dates)
        if err != 0:
            raise Exception('Error in generating ephemeris - errcode %d' % (err))
        # set ephemerides
        for j in range(len(mjdTaiList)):
            eph = ephems[0][j]
            #  dradt = eph[6] - sky motion. Add /n.cos(n.radians(eph[2])) for RA coordinate motion.
            self.Ephemerides[mjdTaiListStr[j]] = Ephemeris(mjdTai=mjdTaiList[j],
                                                           ra=eph[1], dec=eph[2],
                                                           magV=eph[3],
                                                           distance=eph[0],
                                                           dradt=eph[6],
                                                           ddecdt=eph[7])
        return

#################


class Orbit(DayMOPSObject):
    # Inherit underscore getters and setters from DayMOPSObject class

    def __init__(self, q, e, i, node, argPeri, timePeri, epoch, orb_timescale=3.0, format='COM'):
        """Initialize cometary format elements object.

        Requires COMETARY style orbit elements currently."""
        self.setOrbElements(q, e, i, node, argPeri, timePeri, epoch, orb_timescale=orb_timescale)
        return

    def setOrbElements(self, q, e, i, node, argPeri, timePeri, epoch, orb_timescale=3.0, format='COM'):
        """Set cometary format orbital elements for Orbit object.

        COM style elements are: q(AU)/e/i(deg)/node(deg)/argPeri(deg)/timePeri/epoch of orbit combined
        with a timescale for the orbital times (UTC/UT1/TT/TAI = 1/2/3/4) for OpenOrb."""
        if format == 'COM':
            self._q = q
            self._e = e
            self._i = i
            self._node = node
            self._argPeri = argPeri
            self._timePeri = timePeri
            self._epoch = epoch
            self._orb_timescale = 3.0
            # OpenOrb assumes that cometary style orbits use timescale = 3 (TT)
            # TODO : check ranges of q/e/i/node/etc.
        else:
            raise Exception('Only COM (cometary) format orbital elements accepted')
        return

    def __eq__(self, other):
        """Compare orbital elements to check if two sets of orbital elements are exactly the same."""
        if (other == None):
            return False
        if ((self.getq() == other.getq()) and (self.gete() == other.gete()) and
                (self.geti() == other.geti()) and (self.getnode() == other.getnode()) and
                (self.getargPeri() == other.getargPeri()) and (self.gettimePeri() == other.gettimePeri())):
            return True
        else:
            return False

    def propagateOrbElements(self, newepoch):
        """ Propagate a single object to a new epoch, update the orbital parameters.
        This is not the fastest way to propagate orbits for multiple objects - for that, you should
        use movingObjectList function instead."""
        # TBD - don't have this functionality in pyoorb yet
        # propagate ...
        # update orbit
        raise NotImplementedError("Propagate orbital elements not yet implemented in MovingObjects")


###################

class Ephemeris(DayMOPSObject):
    # dayMOPSObject provides integrated getters and setters if needed

    def __init__(self, mjdTai, ra, dec, magV, distance=None,
                 dradt=None, ddecdt=None, ddistancedt=None,
                 magFilter=None, magErr=None, magImsim=None,
                 snr=None, astErr=None, filter=None,
                 solar_elongation=None, cart_x=None, cart_y=None, cart_z=None):
        """ Initialize ephemeris object. 

        Only ra/dec/v_mag are completely necessary, but other info appreciated."""
        self.setEphem(mjdTai=mjdTai, ra=ra, dec=dec, magV=magV, distance=distance,
                      dradt=dradt, ddecdt=ddecdt, ddistancedt=ddistancedt,
                      magFilter=magFilter, magErr=magErr, magImsim=magImsim,
                      snr=snr, astErr=astErr, filter=filter,
                      solar_elongation=solar_elongation,
                      cart_x=cart_x, cart_y=cart_y, cart_z=cart_z)
        return

    def setEphem(self, mjdTai, ra, dec, magV, distance=None,
                 dradt=None, ddecdt=None, ddistancedt=None,
                 magFilter=None, magErr=None, magImsim=None,
                 snr=None, astErr=None, filter=None,
                 solar_elongation=None, cart_x=None, cart_y=None, cart_z=None):
        """Set or update ephemeris object data."""
        self._mjdTai = mjdTai
        # Set the required members of the class - RA/Dec/Vmag.
        self._ra = ra
        self._dec = dec
        # V mag is from the ephemeris calculation, uses H_v and G (comes from pyoorb).
        self._magV = magV
        # These next values may not be set until calculating magnitudes.
        self._filter = filter
        self._magFilter = magFilter
        # Holders for error values, that are useful in catalogs.
        self._astErr = None
        self._magErr = None
        self._snr = None
        self._magImsim = magImsim
        # Set by ephemeris generation
        self._dradt = dradt
        self._ddecdt = ddecdt
        self._distance = distance
        # these are not yet set by ephemeris generation, but will be
        self._ddistancedt = ddistancedt
        self._solar_elongation = solar_elongation
        self._cart_x = cart_x
        self._cart_y = cart_y
        self._cart_z = cart_z
        return

    def getPosition(self):
        """ Return the very basics of the position """
        mjdTai = self.getmjdTai()
        ra = self.getra()
        dec = self.getdec()
        dradt = self.getdradt()
        ddecdt = self.getddecdt()
        magV = self.getmagV()
        return mjdTai, ra, dec, dradt, ddecdt, magV

    def isInFieldofView(self, rafov, decfov, radius_fov):
        """ Return boolean, is the object in the field of view or not """
        """ ra/dec/radius should be in degrees """
        deltara = abs(self._ra - rafov)
        # check wrap on delta RA - assume RA/RA_fov already 0-360
        if deltara > 180.:
            deltara = 360-deltara
        deltadec = abs(self._dec - decfov)
        # print self._ra, self._dec, rafov, decfov, radius_fov, deltara,deltadec
        # assume Dec/Dec_fov already -90-90, so deltadec should be ok
        if deltadec > radius_fov:
            # can't be in field of view
            return False
        val = n.sin(n.radians(deltadec)/2.0)**2.0 +  \
            n.cos(n.radians(self._dec))*n.cos(n.radians(decfov))*(n.sin(n.radians(deltara)/2.)**2.0)
        val = 2.0 * n.arcsin(n.sqrt(val))
        val = n.degrees(val)
        if val < radius_fov:
            return True
        else:
            return False

    def setVariableV_mag(self, var_t0, var_timescale, var_amp):
        """Update V_mag with variability information"""
        # TBD - LJ
        pass

    def calcSNR(image_5sigma):
        """ Calculate the signal to noise of the movingObject at ephemeris['mjdTai'] in filter, """
        """  with background image_5sigma"""
        try:
            self._magFilter
        except AttributeError:
            raise AttributeError, "Need to calculate magnitude in filter bandpass first"
        flux_ratio = n.power(10, 0.4*(image_5sigma - self._magFilter))
        SNR = 5 * (flux_ratio)
        self._snr = SNR
        return SNR


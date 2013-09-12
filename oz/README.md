# Building a glideinWMS Virtual Machine with OZ

OZ is different from BoxGrinder in several rather major ways.

   * Unlike BoxGrinder, OZ will not upload or register your image for you.  Those 
steps are left up to you.
   * any files you want to add to the image must be embedded within the xml template itself.
   * BoxGrinder supported template inheritance, OZ does not


The template included here is a first pass attempt.  As more experience is gained
and the procedures are refined, the template will be updated.

Additional links:

   * [Fedora Wiki Docs](https://fedoraproject.org/wiki/Getting_started_with_OpenStack_Nova#Building_an_Image_With_Oz)
   * [Rackspace Templates](https://github.com/rackerjoe/oz-image-build)


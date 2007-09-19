/* A rewrite of _backend_agg using PyCXX to handle ref counting, etc..
 */

#include <iostream>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <png.h>
#include <time.h>
#include <algorithm>

#include "agg_conv_transform.h"
#include "agg_conv_curve.h"
#include "agg_scanline_storage_aa.h"
#include "agg_scanline_storage_bin.h"
#include "agg_renderer_primitives.h"
#include "agg_span_image_filter_gray.h"
#include "agg_span_interpolator_linear.h"
#include "agg_span_allocator.h"
#include "util/agg_color_conv_rgb8.h"

#include "ft2font.h"
#include "_image.h"
#include "_backend_agg.h"
#include "mplutils.h"

#include "swig_runtime.h"
#include "MPL_isnan.h"

#define PY_ARRAY_TYPES_PREFIX NumPy
#include "numpy/arrayobject.h"
#include "numpy/ufuncobject.h"

#ifndef M_PI
#define M_PI       3.14159265358979323846
#endif
#ifndef M_PI_4
#define M_PI_4     0.785398163397448309616
#endif
#ifndef M_PI_2
#define M_PI_2     1.57079632679489661923
#endif

/** A helper function to convert from a Numpy affine transformation matrix
 *  to an agg::trans_affine.
 */
agg::trans_affine py_to_agg_transformation_matrix(const Py::Object& obj) {
  PyArrayObject* matrix = NULL;
  
  double a = 1.0, b = 0.0, c = 0.0, d = 1.0, e = 0.0, f = 0.0;

  try {
    matrix = (PyArrayObject*) PyArray_ContiguousFromObject(obj.ptr(), PyArray_DOUBLE, 2, 2);
    if (!matrix || matrix->nd != 2 || matrix->dimensions[0] != 3 || matrix->dimensions[1] != 3) {
      throw Py::ValueError("Invalid affine transformation matrix.");
    }

    size_t stride0 = matrix->strides[0];
    size_t stride1 = matrix->strides[1];
    char* row0 = matrix->data;
    char* row1 = row0 + stride0;

    a = *(double*)(row0);
    row0 += stride1;
    c = *(double*)(row0);
    row0 += stride1;
    e = *(double*)(row0);
    
    b = *(double*)(row1);
    row1 += stride1;
    d = *(double*)(row1);
    row1 += stride1;
    f = *(double*)(row1);
  } catch (...) {
    Py_XDECREF(matrix);
  }

  Py_XDECREF(matrix);

  return agg::trans_affine(a, b, c, d, e, f);
}

/** Helper function to get the next vertex in a Numpy array of vertices.
 *  Will generally be used through the GET_NEXT_VERTEX macro.
 */
inline void get_next_vertex(const char* & vertex_i, const char* vertex_end, 
			    double& x, double& y,
			    size_t next_vertex_stride, 
			    size_t next_axis_stride,
			    const char* & code_i, size_t code_stride) {
  if (vertex_i + next_axis_stride >= vertex_end)
    throw Py::ValueError("Error parsing path.  Read past end of vertices");
  x = *(double*)vertex_i;
  y = *(double*)(vertex_i + next_axis_stride);
  vertex_i += next_vertex_stride;
  code_i += code_stride;
}

#define GET_NEXT_VERTEX(x, y) get_next_vertex(vertex_i, vertex_end, x, y, next_vertex_stride, next_axis_stride, code_i, code_stride)

Py::Object BufferRegion::to_string(const Py::Tuple &args) {
  
  // owned=true to prevent memory leak
  return Py::String(PyString_FromStringAndSize((const char*)aggbuf.data,aggbuf.height*aggbuf.stride), true);
}

class PathIterator {
  PyArrayObject* vertices;
  PyArrayObject* codes;
  size_t m_iterator;
  size_t m_total_vertices;

public:
  PathIterator(const Py::Object& path_obj) :
    vertices(NULL), codes(NULL), m_iterator(0) {
    Py::Object vertices_obj = path_obj.getAttr("vertices");
    Py::Object codes_obj = path_obj.getAttr("codes");
    
    vertices = (PyArrayObject*)PyArray_ContiguousFromObject
      (vertices_obj.ptr(), PyArray_DOUBLE, 2, 2);
    if (!vertices || vertices->nd != 2 || vertices->dimensions[1] != 2)
      throw Py::ValueError("Invalid vertices array.");
    codes = (PyArrayObject*)PyArray_ContiguousFromObject
      (codes_obj.ptr(), PyArray_UINT8, 1, 1);
    if (!codes) 
      throw Py::ValueError("Invalid codes array.");
    
    if (codes->dimensions[0] != vertices->dimensions[0])
      throw Py::ValueError("Vertices and codes array are not the same length.");

    m_total_vertices = codes->dimensions[0];
  }

  ~PathIterator() {
    Py_XDECREF(vertices);
    Py_XDECREF(codes);
  }

  static const char code_map[];

  inline unsigned vertex(unsigned idx, double* x, double* y) {
    if (idx > m_total_vertices)
      throw Py::RuntimeError("Requested vertex past end");
    double* pv = (double*)(vertices->data + (idx * vertices->strides[0]));
    *x = *pv++;
    *y = *pv;
    // MGDTODO: Range check
    return code_map[(unsigned int)*(codes->data + (idx * codes->strides[0]))];
  }

  inline unsigned vertex(double* x, double* y) {
    if(m_iterator >= m_total_vertices) return agg::path_cmd_stop;
    return vertex(m_iterator++, x, y);
  }

  inline void rewind(unsigned path_id) {
    m_iterator = path_id;
  }

  inline unsigned total_vertices() {
    return m_total_vertices;
  }
};

const char PathIterator::code_map[] = {0, 
				       agg::path_cmd_move_to, 
				       agg::path_cmd_line_to, 
				       agg::path_cmd_curve3,
				       agg::path_cmd_curve4,
				       agg::path_cmd_end_poly | agg::path_flags_close};

GCAgg::GCAgg(const Py::Object &gc, double dpi, bool snapto) :
  dpi(dpi), snapto(snapto), isaa(true), linewidth(1.0), alpha(1.0),
  cliprect(NULL), clippath(NULL), 
  Ndash(0), dashOffset(0.0), dasha(NULL)
{
  _VERBOSE("GCAgg::GCAgg");
  linewidth = points_to_pixels ( gc.getAttr("_linewidth") ) ;
  alpha = Py::Float( gc.getAttr("_alpha") );
  color = get_color(gc);
  _set_antialiased(gc);
  _set_linecap(gc);
  _set_joinstyle(gc);
  _set_dashes(gc);
  _set_clip_rectangle(gc);
  _set_clip_path(gc);
}

void
GCAgg::_set_antialiased(const Py::Object& gc) {
  _VERBOSE("GCAgg::antialiased");
  isaa = Py::Int( gc.getAttr( "_antialiased") );
}

agg::rgba
GCAgg::get_color(const Py::Object& gc) {
  _VERBOSE("GCAgg::get_color");
  Py::Tuple rgb = Py::Tuple( gc.getAttr("_rgb") );
  
  double alpha = Py::Float( gc.getAttr("_alpha") );
  
  double r = Py::Float(rgb[0]);
  double g = Py::Float(rgb[1]);
  double b = Py::Float(rgb[2]);
  return agg::rgba(r, g, b, alpha);
}

double
GCAgg::points_to_pixels( const Py::Object& points) {
  _VERBOSE("GCAgg::points_to_pixels");
  double p = Py::Float( points ) ;
  return p * dpi/72.0;
}

void
GCAgg::_set_linecap(const Py::Object& gc) {
  _VERBOSE("GCAgg::_set_linecap");
  
  std::string capstyle = Py::String( gc.getAttr( "_capstyle" ) );

  if (capstyle=="butt")
    cap = agg::butt_cap;
  else if (capstyle=="round")
    cap = agg::round_cap;
  else if(capstyle=="projecting")
    cap = agg::square_cap;
  else
    throw Py::ValueError(Printf("GC _capstyle attribute must be one of butt, round, projecting; found %s", capstyle.c_str()).str());
}

void
GCAgg::_set_joinstyle(const Py::Object& gc) {
  _VERBOSE("GCAgg::_set_joinstyle");
  
  std::string joinstyle = Py::String( gc.getAttr("_joinstyle") );
  
  if (joinstyle=="miter")
    join =  agg::miter_join;
  else if (joinstyle=="round")
    join = agg::round_join;
  else if(joinstyle=="bevel")
    join = agg::bevel_join;
  else
    throw Py::ValueError(Printf("GC _joinstyle attribute must be one of butt, round, projecting; found %s", joinstyle.c_str()).str());
}

void
GCAgg::_set_dashes(const Py::Object& gc) {
  //return the dashOffset, dashes sequence tuple.
  _VERBOSE("GCAgg::_set_dashes");
  
  delete [] dasha;
  dasha = NULL;
  
  Py::Tuple dashtup = gc.getAttr("_dashes");
  
  if (dashtup.length()!=2)
    throw Py::ValueError(Printf("GC dashtup must be a length 2 tuple; found %d", dashtup.length()).str());
  
  
  bool useDashes = dashtup[0].ptr() != Py_None;
  
  if ( !useDashes ) return;
  
  dashOffset = points_to_pixels(dashtup[0]);
  Py::SeqBase<Py::Object> dashSeq;
  dashSeq = dashtup[1];
  
  Ndash = dashSeq.length();
  if (Ndash%2 != 0  )
    throw Py::ValueError(Printf("dash sequence must be an even length sequence; found %d", Ndash).str());
  
  dasha = new double[Ndash];
  double val;
  for (size_t i=0; i<Ndash; i++) {
    val = points_to_pixels(dashSeq[i]);
    if (this->snapto) val = (int)val +0.5;
    dasha[i] = val;
  }
}

// MGDTODO: Convert directly from Bbox object (numpy)
void
GCAgg::_set_clip_rectangle( const Py::Object& gc) {
  //set the clip rectangle from the gc
  
  _VERBOSE("GCAgg::_set_clip_rectangle");
  
  delete [] cliprect;
  cliprect = NULL;
  
  Py::Object o ( gc.getAttr( "_cliprect" ) );
  if (o.ptr() == Py_None) {
    return;
  }
  
  Py::SeqBase<Py::Object> rect( o );
  
  double l = Py::Float(rect[0]) ;
  double b = Py::Float(rect[1]) ;
  double w = Py::Float(rect[2]) ;
  double h = Py::Float(rect[3]) ;
  
  cliprect = new double[4];
  //todo check for memory alloc failure
  cliprect[0] = l;
  cliprect[1] = b;
  cliprect[2] = w;
  cliprect[3] = h;
}

void
GCAgg::_set_clip_path( const Py::Object& gc) {
  //set the clip path from the gc
  
  _VERBOSE("GCAgg::_set_clip_path");
  
  Py_XINCREF(clippath);
  clippath = NULL;
  
  Py::Object o = gc.getAttr("_clippath");
  if (o.ptr()==Py_None) {
    return;
  }
  
  clippath = new PathAgg(o);
}


const size_t
RendererAgg::PIXELS_PER_INCH(96);

RendererAgg::RendererAgg(unsigned int width, unsigned int height, double dpi,
			 int debug) :
  width(width),
  height(height),
  dpi(dpi),
  NUMBYTES(width*height*4),
  debug(debug),
  lastclippath(NULL)
{
  _VERBOSE("RendererAgg::RendererAgg");
  unsigned stride(width*4);
  
  
  pixBuffer = new agg::int8u[NUMBYTES];
  renderingBuffer = new agg::rendering_buffer;
  renderingBuffer->attach(pixBuffer, width, height, stride);
  
  alphaBuffer = new agg::int8u[NUMBYTES];
  alphaMaskRenderingBuffer = new agg::rendering_buffer;
  alphaMaskRenderingBuffer->attach(alphaBuffer, width, height, stride);
  alphaMask = new alpha_mask_type(*alphaMaskRenderingBuffer);
  //jdh
  pixfmtAlphaMask = new agg::pixfmt_gray8(*alphaMaskRenderingBuffer);
  rendererBaseAlphaMask = new renderer_base_alpha_mask_type(*pixfmtAlphaMask);
  rendererAlphaMask = new renderer_alpha_mask_type(*rendererBaseAlphaMask);
  scanlineAlphaMask = new agg::scanline_p8();
  
  
  slineP8 = new scanline_p8;
  slineBin = new scanline_bin;
  
  
  pixFmt = new pixfmt(*renderingBuffer);
  rendererBase = new renderer_base(*pixFmt);
  rendererBase->clear(agg::rgba(1, 1, 1, 0));
  
  rendererAA = new renderer_aa(*rendererBase);
  rendererBin = new renderer_bin(*rendererBase);
  theRasterizer = new rasterizer();
  //theRasterizer->filling_rule(agg::fill_even_odd);
  //theRasterizer->filling_rule(agg::fill_non_zero);
  
};



void
RendererAgg::set_clipbox_rasterizer(double *cliprect) {
  //set the clip rectangle from the gc
  
  _VERBOSE("RendererAgg::set_clipbox_rasterizer");

  theRasterizer->reset_clipping();
  rendererBase->reset_clipping(true);

  if (cliprect!=NULL) {
    
    double l = cliprect[0] ;
    double b = cliprect[1] ;
    double w = cliprect[2] ;
    double h = cliprect[3] ;
    
    theRasterizer->clip_box(l, height-(b+h),
			    l+w, height-b);
  }
  _VERBOSE("RendererAgg::set_clipbox_rasterizer done");
  
}

std::pair<bool, agg::rgba>
RendererAgg::_get_rgba_face(const Py::Object& rgbFace, double alpha) {
  _VERBOSE("RendererAgg::_get_rgba_face");
  std::pair<bool, agg::rgba> face;
  
  if (rgbFace.ptr() == Py_None) {
    face.first = false;
  }
  else {
    face.first = true;
    Py::Tuple rgb = Py::Tuple(rgbFace);
    face.second = rgb_to_color(rgb, alpha);
  }
  return face;
  
}

SnapData
SafeSnap::snap (const float& x, const float& y) {
  xsnap = (int)x + 0.5;
  ysnap = (int)y + 0.5;
  
  if ( first || ( (xsnap!=lastxsnap) || (ysnap!=lastysnap) ) ) {
    lastxsnap = xsnap;
    lastysnap = ysnap;
    lastx = x;
    lasty = y;
    first = false;
    return SnapData(true, xsnap, ysnap);
  }

  // ok both are equal and we need to do an offset
  if ( (x==lastx) && (y==lasty) ) {
    // no choice but to return equal coords; set newpoint = false
    lastxsnap = xsnap;
    lastysnap = ysnap;
    lastx = x;
    lasty = y;
    return SnapData(false, xsnap, ysnap);    
  }

  // ok the real points are not identical but the rounded ones, so do
  // a one pixel offset
  if (x>lastx) xsnap += 1.;
  else if (x<lastx) xsnap -= 1.;

  if (y>lasty) ysnap += 1.;
  else if (y<lasty) ysnap -= 1.;

  lastxsnap = xsnap;
  lastysnap = ysnap;
  lastx = x;
  lasty = y;
  return SnapData(true, xsnap, ysnap);    
}  
		 



Py::Object
RendererAgg::copy_from_bbox(const Py::Tuple& args) {
  //copy region in bbox to buffer and return swig/agg buffer object
  args.verify_length(1);
  
  
  agg::rect r = bbox_to_rect<int>(args[0]);
  /*
    r.x1 -=5;
    r.y1 -=5;
    r.x2 +=5;
    r.y2 +=5;
  */
  int boxwidth = r.x2-r.x1;
  int boxheight = r.y2-r.y1;
  int boxstride = boxwidth*4;
  agg::buffer buf(boxwidth, boxheight, boxstride, false);
  if (buf.data ==NULL) {
    throw Py::MemoryError("RendererAgg::copy_from_bbox could not allocate memory for buffer");
  }
  
  agg::rendering_buffer rbuf;
  rbuf.attach(buf.data, boxwidth, boxheight, boxstride);
  
  pixfmt pf(rbuf);
  renderer_base rb(pf);
  //rb.clear(agg::rgba(1, 0, 0)); //todo remove me
  rb.copy_from(*renderingBuffer, &r, -r.x1, -r.y1);
  BufferRegion* reg = new BufferRegion(buf, r, true);
  return Py::asObject(reg);
}

Py::Object
RendererAgg::restore_region(const Py::Tuple& args) {
  //copy BufferRegion to buffer
  args.verify_length(1);
  BufferRegion* region  = static_cast<BufferRegion*>(args[0].ptr());
  
  if (region->aggbuf.data==NULL)
    return Py::Object();
  //throw Py::ValueError("Cannot restore_region from NULL data");
  
  
  agg::rendering_buffer rbuf;
  rbuf.attach(region->aggbuf.data,
	      region->aggbuf.width,
	      region->aggbuf.height,
	      region->aggbuf.stride);
  
  rendererBase->copy_from(rbuf, 0, region->rect.x1, region->rect.y1);
  
  return Py::Object();
}

/**
 * Helper function to convert a Python Bbox object to an agg rectangle
 */
template<class T>
agg::rect_base<T>
RendererAgg::bbox_to_rect(const Py::Object& o) {
  //return the agg::rect for bbox, flipping y
  PyArrayObject *bbox = (PyArrayObject *) PyArray_ContiguousFromObject(o.ptr(), PyArray_DOUBLE, 2, 2);

  if (!bbox || bbox->nd != 2 || bbox->dimensions[0] != 2 || bbox->dimensions[1] != 2)
    throw Py::TypeError
      ("Expected a Bbox object.");

  double l = bbox->data[0];
  double b = bbox->data[1];
  double r = bbox->data[2];
  double t = bbox->data[3];
  T height = (T)(b - t);
  
  agg::rect_base<T> rect((T)l, height-(T)t, (T)r, height-(T)b ) ;
  if (!rect.is_valid())
    throw Py::ValueError("Invalid rectangle in bbox_to_rect");
  return rect;
}

void
RendererAgg::set_clip_from_bbox(const Py::Object& o) {
  
  // do not puut this in the else below.  We want to unconditionally
  // clear the clip
  theRasterizer->reset_clipping();
  rendererBase->reset_clipping(true);
  
  if (o.ptr() != Py_None) {  //using clip
    // Bbox::check(args[0]) failing; something about cross module?
    // set the clip rectangle
    // flipy
    agg::rect_base<double> r = bbox_to_rect<double>(o);
    theRasterizer->clip_box(r.x1, r.y1, r.x2, r.y2);
    rendererBase->clip_box((int)r.x1, (int)r.y1, (int)r.x2, (int)r.y2);
  }
  
}

/****************************/

int RendererAgg::intersectCheck(double yCoord, double x1, double y1, double x2, double y2, int* intersectPoint)
{
  /* Returns 0 if no intersection or 1 if yes */
  /* If yes, changes intersectPoint to the x coordinate of the point of intersection */
  if ((y1>=yCoord) != (y2>=yCoord)) {
    /* Don't need to check for y1==y2 because the above condition rejects it automatically */
    *intersectPoint = (int)( ( x1 * (y2 - yCoord) + x2 * (yCoord - y1) ) / (y2 - y1) + 0.5);
    return 1;
  }
  return 0;
}

int RendererAgg::inPolygon(int row, const double xs[4], const double ys[4], int col[4])
{
  int numIntersect = 0;
  int i;
  /* Determines the boundaries of the row of pixels that is in the polygon */
  /* A pixel (x, y) is in the polygon if its center (x+0.5, y+0.5) is */
  double ycoord = (double(row) + 0.5);
  for(i=0; i<=3; i++)
    numIntersect += intersectCheck(ycoord, xs[i], ys[i], xs[(i+1)%4], ys[(i+1)%4], col+numIntersect);
  
  /* reorder if necessary */
  if (numIntersect == 2 && col[0] > col[1]) std::swap(col[0],col[1]);
  if (numIntersect == 4) {
    // Inline bubble sort on array of size 4
    if (col[0] > col[1]) std::swap(col[0],col[1]);
    if (col[1] > col[2]) std::swap(col[1],col[2]);
    if (col[2] > col[3]) std::swap(col[2],col[3]);
    if (col[0] > col[1]) std::swap(col[0],col[1]);
    if (col[1] > col[2]) std::swap(col[1],col[2]);
    if (col[0] > col[1]) std::swap(col[0],col[1]);
  }
  // numIntersect must be 0, 2 or 4
  return numIntersect;
}


Py::Object
RendererAgg::draw_markers(const Py::Tuple& args) {
  typedef agg::conv_transform<agg::path_storage> transformed_path_t;
  typedef agg::conv_curve<transformed_path_t> curve_t;
  typedef agg::conv_stroke<curve_t> stroke_t;
  typedef agg::conv_dash<curve_t> dash_t;
  typedef agg::conv_stroke<dash_t> stroke_dash_t;

  theRasterizer->reset_clipping();
  
  args.verify_length(7);
  
  GCAgg gc = GCAgg(args[0], dpi);
  Py::Object marker_path_obj = args[1];
  if (!PathAgg::check(marker_path_obj))
    throw Py::TypeError("Native path object is not of correct type");
  PathAgg* marker_path = static_cast<PathAgg*>(marker_path_obj.ptr());
  agg::trans_affine marker_trans = py_to_agg_transformation_matrix(args[2]);
  Py::Object vertices_obj = args[3];
  Py::Object codes_obj = args[4];
  agg::trans_affine trans = py_to_agg_transformation_matrix(args[5]);
  facepair_t face = _get_rgba_face(args[6], gc.alpha);

  // Deal with the difference in y-axis direction
  marker_trans *= agg::trans_affine_scaling(1.0, -1.0);
  trans *= agg::trans_affine_scaling(1.0, -1.0);
  trans *= agg::trans_affine_translation(0.0, (double)height);
  
  marker_path->rewind(0);
  transformed_path_t marker_path_transformed(*marker_path, marker_trans);
  curve_t marker_path_curve(marker_path_transformed);
  
  //maxim's suggestions for cached scanlines
  agg::scanline_storage_aa8 scanlines;
  theRasterizer->reset();
  
  agg::int8u* fillCache = NULL;
  agg::int8u* strokeCache = NULL;
  PyArrayObject* vertices = NULL;
  PyArrayObject* codes = NULL;

  try {
    vertices = (PyArrayObject*)PyArray_ContiguousFromObject
      (vertices_obj.ptr(), PyArray_DOUBLE, 2, 2);
    if (!vertices || vertices->nd != 2 || vertices->dimensions[1] != 2)
      throw Py::ValueError("Invalid vertices array.");
    codes = (PyArrayObject*)PyArray_ContiguousFromObject
      (codes_obj.ptr(), PyArray_UINT8, 1, 1);
    if (!codes) 
      throw Py::ValueError("Invalid codes array.");

    unsigned fillSize = 0;
    if (face.first) {
      theRasterizer->add_path(marker_path_curve);
      agg::render_scanlines(*theRasterizer, *slineP8, scanlines);
      fillSize = scanlines.byte_size();
      fillCache = new agg::int8u[fillSize]; // or any container
      scanlines.serialize(fillCache);
    }
  
    stroke_t stroke(marker_path_curve);
    stroke.width(gc.linewidth);
    stroke.line_cap(gc.cap);
    stroke.line_join(gc.join);
    theRasterizer->reset();
    theRasterizer->add_path(stroke);
    agg::render_scanlines(*theRasterizer, *slineP8, scanlines);
    unsigned strokeSize = scanlines.byte_size();
    strokeCache = new agg::int8u[strokeSize]; // or any container
    scanlines.serialize(strokeCache);

    // MGDTODO: Clean this up and support clippaths as well
    theRasterizer->reset_clipping();
    if (gc.cliprect==NULL) {
      rendererBase->reset_clipping(true);
    }
    else {
      int l = (int)(gc.cliprect[0]) ;
      int b = (int)(gc.cliprect[1]) ;
      int w = (int)(gc.cliprect[2]) ;
      int h = (int)(gc.cliprect[3]) ;
      rendererBase->clip_box(l, height-(b+h),l+w, height-b);
    }
    
    size_t next_vertex_stride = vertices->strides[0];
    size_t next_axis_stride = vertices->strides[1];
    size_t code_stride = codes->strides[0];

    const char* vertex_i = vertices->data;
    const char* code_i = codes->data;
    const char* vertex_end = vertex_i + (vertices->dimensions[0] * vertices->strides[0]);

    size_t N = codes->dimensions[0];
    double x, y;

    agg::serialized_scanlines_adaptor_aa8 sa;
    agg::serialized_scanlines_adaptor_aa8::embedded_scanline sl;

    for (size_t i=0; i < N; i++) {
      size_t num_vertices = NUM_VERTICES[(int)(*code_i)];
      if (num_vertices) {
	for (size_t j=0; j<num_vertices; ++j)
	  GET_NEXT_VERTEX(x, y);
	if (*code_i == STOP || *code_i == CLOSEPOLY)
	  continue;

	trans.transform(&x, &y);
	
	if (face.first) {
	  //render the fill
	  sa.init(fillCache, fillSize, x, y);
	  rendererAA->color(face.second);
	  agg::render_scanlines(sa, sl, *rendererAA);
	}

	//render the stroke
	sa.init(strokeCache, strokeSize, x, y);
	rendererAA->color(gc.color);
	agg::render_scanlines(sa, sl, *rendererAA);
      }
      code_i += code_stride;
    }
  } catch(...) {
    Py_XDECREF(vertices);
    Py_XDECREF(codes);
    delete[] fillCache;
    delete[] strokeCache;
  }
  
  Py_XDECREF(vertices);
  Py_XDECREF(codes);
  delete [] fillCache;
  delete [] strokeCache;

  return Py::Object();
  
}


/**
 * This is a custom span generator that converts spans in the 
 * 8-bit inverted greyscale font buffer to rgba that agg can use.
 */
template<
  class ColorT,
  class ChildGenerator>
class font_to_rgba :
  public agg::span_generator<ColorT, 
			     agg::span_allocator<ColorT> >
{
public:
  typedef ChildGenerator child_type;
  typedef ColorT color_type;
  typedef agg::span_allocator<color_type> allocator_type;
  typedef agg::span_generator<
    ColorT, 
    agg::span_allocator<ColorT> > base_type;

private:
  child_type* _gen;
  allocator_type _alloc;
  color_type _color;
  
public:
  font_to_rgba(child_type* gen, color_type color) : 
    base_type(_alloc),
    _gen(gen),
    _color(color) {
  }

  color_type* generate(int x, int y, unsigned len)
  {
    color_type* dst = base_type::allocator().span();

    typename child_type::color_type* src = _gen->generate(x, y, len);

    do {
      *dst = _color;
      dst->a = src->v;
      ++src;
      ++dst;
    } while (--len);

    return base_type::allocator().span();
  }

  void prepare(unsigned max_span_len) 
  {
    _alloc.allocate(max_span_len);
    _gen->prepare(max_span_len);
  }

};

Py::Object
RendererAgg::draw_text_image(const Py::Tuple& args) {
  _VERBOSE("RendererAgg::draw_text");

  typedef agg::span_interpolator_linear<> interpolator_type;
  typedef agg::span_image_filter_gray<agg::gray8, interpolator_type> 
    image_span_gen_type;
  typedef font_to_rgba<pixfmt::color_type, image_span_gen_type> 
    span_gen_type;
  typedef agg::renderer_scanline_aa<renderer_base, span_gen_type> 
    renderer_type;
  
  args.verify_length(5);
  
  FT2Image *image = static_cast<FT2Image*>(args[0].ptr());
  if (!image->get_buffer())
    return Py::Object();
  
  int x(0),y(0);
  try {
    x = Py::Int( args[1] );
    y = Py::Int( args[2] );
  }
  catch (Py::TypeError) {
    //x,y out of range; todo issue warning?
    return Py::Object();
  }
  
  double angle = Py::Float( args[3] );

  GCAgg gc = GCAgg(args[4], dpi);
  
  set_clipbox_rasterizer(gc.cliprect);

  const unsigned char* const buffer = image->get_buffer();
  agg::rendering_buffer srcbuf
    ((agg::int8u*)buffer, image->get_width(), 
     image->get_height(), image->get_width());
  agg::pixfmt_gray8 pixf_img(srcbuf);
  
  agg::trans_affine mtx;
  mtx *= agg::trans_affine_translation(0, -(int)image->get_height());
  mtx *= agg::trans_affine_rotation(-angle * agg::pi / 180.0);
  mtx *= agg::trans_affine_translation(x, y);

  agg::path_storage rect;
  rect.move_to(0, 0);
  rect.line_to(image->get_width(), 0);
  rect.line_to(image->get_width(), image->get_height());
  rect.line_to(0, image->get_height());
  rect.line_to(0, 0);
  agg::conv_transform<agg::path_storage> rect2(rect, mtx);

  agg::trans_affine inv_mtx(mtx);
  inv_mtx.invert();

  agg::image_filter_lut filter;
  filter.calculate(agg::image_filter_spline36());
  interpolator_type interpolator(inv_mtx);
  agg::span_allocator<agg::gray8> gray_span_allocator;
  image_span_gen_type image_span_generator(gray_span_allocator, 
					   srcbuf, 0, interpolator, filter);
  span_gen_type output_span_generator(&image_span_generator, gc.color);
  renderer_type ri(*rendererBase, output_span_generator);
  agg::rasterizer_scanline_aa<> rasterizer;
  agg::scanline_p8 scanline;
  rasterizer.add_path(rect2);
  agg::render_scanlines(rasterizer, scanline, ri);
  
  return Py::Object();
}


Py::Object
RendererAgg::draw_image(const Py::Tuple& args) {
  _VERBOSE("RendererAgg::draw_image");
  args.verify_length(4);
  
  float x = Py::Float(args[0]);
  float y = Py::Float(args[1]);
  Image *image = static_cast<Image*>(args[2].ptr());
  
  set_clip_from_bbox(args[3]);
  
  pixfmt pixf(*(image->rbufOut));
  
  
  Py::Tuple empty;
  image->flipud_out(empty);
  rendererBase->blend_from(pixf, 0, (int)x, (int)(height-(y+image->rowsOut)));
  image->flipud_out(empty);
  
  
  return Py::Object();
  
}

Py::Object
RendererAgg::convert_to_native_path(const Py::Tuple& args) {
  _VERBOSE("RendererAgg::draw_image");
  args.verify_length(1);
  
  Py::Object path = args[0];

  return Py::asObject(new PathAgg(path));
}

  
PathAgg::PathAgg(const Py::Object& path_obj) : curvy(false) {
  Py::Object vertices_obj = path_obj.getAttr("vertices");
  Py::Object codes_obj = path_obj.getAttr("codes");
  
  PyArrayObject* vertices = NULL;
  PyArrayObject* codes = NULL;

  try {
    vertices = (PyArrayObject*)PyArray_ContiguousFromObject
      (vertices_obj.ptr(), PyArray_DOUBLE, 2, 2);
    if (!vertices || vertices->nd != 2 || vertices->dimensions[1] != 2)
      throw Py::ValueError("Invalid vertices array.");
    codes = (PyArrayObject*)PyArray_ContiguousFromObject
      (codes_obj.ptr(), PyArray_UINT8, 1, 1);
    if (!codes) 
      throw Py::ValueError("Invalid codes array.");

    size_t next_vertex_stride = vertices->strides[0];
    size_t next_axis_stride = vertices->strides[1];
    size_t code_stride = codes->strides[0];

    const char* vertex_i = vertices->data;
    const char* code_i = codes->data;
    const char* vertex_end = vertex_i + (vertices->dimensions[0] * vertices->strides[0]);

    size_t N = codes->dimensions[0];
    double x0, y0, x1, y1, x2, y2;

    for (size_t i = 0; i < N; ++i) {
      switch (*(unsigned char*)(code_i)) {
      case STOP:
	GET_NEXT_VERTEX(x0, y0);
	_VERBOSE("STOP");
	// MGDTODO: If this isn't the end, we should raise an error
	break;
      case MOVETO:
	GET_NEXT_VERTEX(x0, y0);
	move_to(x0, y0);
	_VERBOSE("MOVETO");
	break;
      case LINETO:
	GET_NEXT_VERTEX(x0, y0);
	line_to(x0, y0);
	_VERBOSE("LINETO");
	break;
      case CURVE3:
	GET_NEXT_VERTEX(x0, y0);
	GET_NEXT_VERTEX(x1, y1);
	curve3(x0, y0, x1, y1);
	curvy = true;
	_VERBOSE("CURVE3");
	break;
      case CURVE4:
	GET_NEXT_VERTEX(x0, y0);
	GET_NEXT_VERTEX(x1, y1);
	GET_NEXT_VERTEX(x2, y2);
	curve4(x0, y0, x1, y1, x2, y2);
	curvy = true;
	_VERBOSE("CURVE4");
	break;
      case CLOSEPOLY:
	close_polygon();
	GET_NEXT_VERTEX(x0, y0);
	_VERBOSE("CLOSEPOLY");
	break;
      }
    }
  } catch(...) {
    Py_XDECREF(vertices);
    Py_XDECREF(codes);
    throw;
  }

  Py_XDECREF(vertices);
  Py_XDECREF(codes);
}

Py::Object
RendererAgg::draw_path(const Py::Tuple& args) {
  typedef agg::conv_transform<PathIterator> transformed_path_t;
  typedef agg::conv_curve<transformed_path_t> curve_t;
  typedef agg::conv_stroke<curve_t> stroke_t;
  typedef agg::conv_dash<curve_t> dash_t;
  typedef agg::conv_stroke<dash_t> stroke_dash_t;
  typedef agg::pixfmt_amask_adaptor<pixfmt, alpha_mask_type> pixfmt_amask_type;
  typedef agg::renderer_base<pixfmt_amask_type> amask_ren_type;
  typedef agg::renderer_scanline_aa_solid<amask_ren_type> amask_aa_renderer_type;
  typedef agg::renderer_scanline_bin_solid<amask_ren_type> amask_bin_renderer_type;

  theRasterizer->reset_clipping();
  
  _VERBOSE("RendererAgg::draw_path");
  args.verify_length(4);

  GCAgg gc = GCAgg(args[0], dpi);
  Py::Object path_obj = args[1];
//   if (!PathAgg::check(path_obj))
//     throw Py::TypeError("Native path object is not of correct type");
  // PathAgg* path = static_cast<PathAgg*>(path_obj.ptr());
  PathIterator path(path_obj);

  agg::trans_affine trans = py_to_agg_transformation_matrix(args[2]);
  facepair_t face = _get_rgba_face(args[3], gc.alpha);

  trans *= agg::trans_affine_scaling(1.0, -1.0);
  trans *= agg::trans_affine_translation(0.0, (double)height);

  transformed_path_t* tpath = NULL;
  agg::path_storage new_path;

  bool has_clippath = (gc.clippath != NULL);

  if (has_clippath && (gc.clippath != lastclippath || trans != lastclippath_transform)) {
//     rendererBaseAlphaMask->clear(agg::gray8(0, 0));
//     gc.clippath->rewind(0);
//     transformed_path_t transformed_clippath(*(gc.clippath), trans);
//     theRasterizer->add_path(transformed_clippath);
//     rendererAlphaMask->color(agg::gray8(255, 255));
//     agg::render_scanlines(*theRasterizer, *scanlineAlphaMask, *rendererAlphaMask);
//     lastclippath = gc.clippath;
//     lastclippath_transform = trans;
  }

  try {
    // If this is a straight horizontal or vertical line, quantize to nearest 
    // pixels
//     if (path.total_vertices() == 2) {
//       double x0, y0, x1, y1;
//       path.vertex(0, &x0, &y0);
//       trans.transform(&x0, &y0);
//       path.vertex(1, &x1, &y1);
//       trans.transform(&x1, &y1);
//       if (((int)x0 == (int)x1) || ((int)y0 == (int)y1)) {
// 	new_path.move_to((int)x0 + 0.5, (int)y0 + 0.5);
// 	new_path.line_to((int)x1 + 0.5, (int)y1 + 0.5);
// 	tpath = new transformed_path_t(new_path, agg::trans_affine());
//       }
//     }

    if (!tpath) {
      tpath = new transformed_path_t(path, trans);
    }

    // Benchmarking shows that there is no noticable slowdown to always
    // treating paths as having curved segments.  Doing so greatly 
    // simplifies the code
    curve_t curve(*tpath);
    
    set_clipbox_rasterizer(gc.cliprect);
    
    if (face.first) {
      if (has_clippath) {
	pixfmt_amask_type pfa(*pixFmt, *alphaMask);
	amask_ren_type r(pfa);
	amask_aa_renderer_type ren(r);
	ren.color(gc.color);
	agg::render_scanlines(*theRasterizer, *slineP8, ren);
      } else{
	rendererAA->color(face.second);
	theRasterizer->add_path(curve);
	agg::render_scanlines(*theRasterizer, *slineP8, *rendererAA);
      }
    }
    
    if (gc.linewidth) {
      if (gc.dasha == NULL) {
	stroke_t stroke(curve);
	stroke.width(gc.linewidth);
	stroke.line_cap(gc.cap);
	stroke.line_join(gc.join);
	theRasterizer->add_path(stroke);
      } else {
 	dash_t dash(curve);
	for (size_t i = 0; i < (gc.Ndash / 2); ++i)
	dash.add_dash(gc.dasha[2 * i], gc.dasha[2 * i + 1]);
	stroke_dash_t stroke(dash);
	stroke.line_cap(gc.cap);
	stroke.line_join(gc.join);
	stroke.width(gc.linewidth);
	theRasterizer->add_path(stroke);
      }
    
      if (gc.isaa) {
	if (has_clippath) {
	  pixfmt_amask_type pfa(*pixFmt, *alphaMask);
	  amask_ren_type r(pfa);
	  amask_aa_renderer_type ren(r);
	  ren.color(gc.color);
	  agg::render_scanlines(*theRasterizer, *slineP8, ren);
	} else {
	  rendererAA->color(gc.color);
	  agg::render_scanlines(*theRasterizer, *slineP8, *rendererAA);
	}
      } else {
	if (has_clippath) {
	  pixfmt_amask_type pfa(*pixFmt, *alphaMask);
	  amask_ren_type r(pfa);
	  amask_bin_renderer_type ren(r);
	  ren.color(gc.color);
	  agg::render_scanlines(*theRasterizer, *slineP8, ren);
	} else {
	  rendererBin->color(gc.color);
	  agg::render_scanlines(*theRasterizer, *slineBin, *rendererBin);
	}
      }
    }
  } catch (...) {
    delete tpath;
    throw;
  }
  
  delete tpath;

  return Py::Object();
}


Py::Object
RendererAgg::write_rgba(const Py::Tuple& args) {
  _VERBOSE("RendererAgg::write_rgba");
  
  args.verify_length(1);
  std::string fname = Py::String( args[0]);
  
  std::ofstream of2( fname.c_str(), std::ios::binary|std::ios::out);
  for (size_t i=0; i<NUMBYTES; i++) {
    of2.write((char*)&(pixBuffer[i]), sizeof(char));
  }
  return Py::Object();
  
}


// this code is heavily adapted from the paint license, which is in
// the file paint.license (BSD compatible) included in this
// distribution.  TODO, add license file to MANIFEST.in and CVS
Py::Object
RendererAgg::write_png(const Py::Tuple& args)
{
  _VERBOSE("RendererAgg::write_png");
  
  args.verify_length(1);
  
  FILE *fp;
  Py::Object o = Py::Object(args[0]);
  bool fpclose = true;
  if (o.isString()) {
    std::string fileName = Py::String(o);
    const char *file_name = fileName.c_str();
    if ((fp = fopen(file_name, "wb")) == NULL)
      throw Py::RuntimeError( Printf("Could not open file %s", file_name).str() );
  }
  else {
    if ((fp = PyFile_AsFile(o.ptr())) == NULL)
      throw Py::TypeError("Could not convert object to file pointer");
    fpclose = false;
  }
  
  png_structp png_ptr;
  png_infop info_ptr;
  struct        png_color_8_struct sig_bit;
  png_uint_32 row;
  
  png_bytep *row_pointers = new png_bytep[height];
  for (row = 0; row < height; ++row) {
    row_pointers[row] = pixBuffer + row * width * 4;
  }
  
  
  if (fp == NULL) {
    delete [] row_pointers;
    throw Py::RuntimeError("Could not open file");
  }
  
  
  png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
  if (png_ptr == NULL) {
    if (fpclose) fclose(fp);
    delete [] row_pointers;
    throw Py::RuntimeError("Could not create write struct");
  }
  
  info_ptr = png_create_info_struct(png_ptr);
  if (info_ptr == NULL) {
    if (fpclose) fclose(fp);
    png_destroy_write_struct(&png_ptr, &info_ptr);
    delete [] row_pointers;
    throw Py::RuntimeError("Could not create info struct");
  }
  
  if (setjmp(png_ptr->jmpbuf)) {
    if (fpclose) fclose(fp);
    png_destroy_write_struct(&png_ptr, &info_ptr);
    delete [] row_pointers;
    throw Py::RuntimeError("Error building image");
  }
  
  png_init_io(png_ptr, fp);
  png_set_IHDR(png_ptr, info_ptr,
	       width, height, 8,
	       PNG_COLOR_TYPE_RGB_ALPHA, PNG_INTERLACE_NONE,
	       PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);
  
  // this a a color image!
  sig_bit.gray = 0;
  sig_bit.red = 8;
  sig_bit.green = 8;
  sig_bit.blue = 8;
  /* if the image has an alpha channel then */
  sig_bit.alpha = 8;
  png_set_sBIT(png_ptr, info_ptr, &sig_bit);
  
  png_write_info(png_ptr, info_ptr);
  png_write_image(png_ptr, row_pointers);
  png_write_end(png_ptr, info_ptr);
  
  /* Changed calls to png_destroy_write_struct to follow
     http://www.libpng.org/pub/png/libpng-manual.txt.
     This ensures the info_ptr memory is released.
  */
  
  png_destroy_write_struct(&png_ptr, &info_ptr);
  
  delete [] row_pointers;
  
  if (fpclose) fclose(fp);
  
  return Py::Object();
}


Py::Object
RendererAgg::tostring_rgb(const Py::Tuple& args) {
  //"Return the rendered buffer as an RGB string";
  
  _VERBOSE("RendererAgg::tostring_rgb");
  
  args.verify_length(0);
  int row_len = width*3;
  unsigned char* buf_tmp = new unsigned char[row_len * height];
  if (buf_tmp ==NULL) {
    //todo: also handle allocation throw
    throw Py::MemoryError("RendererAgg::tostring_rgb could not allocate memory");
  }
  agg::rendering_buffer renderingBufferTmp;
  renderingBufferTmp.attach(buf_tmp,
			    width,
			    height,
			    row_len);
  
  agg::color_conv(&renderingBufferTmp, renderingBuffer, agg::color_conv_rgba32_to_rgb24());
  
  
  //todo: how to do this with native CXX
  PyObject* o = Py_BuildValue("s#",
			      buf_tmp,
			      row_len * height);
  delete [] buf_tmp;
  return Py::asObject(o);
}


Py::Object
RendererAgg::tostring_argb(const Py::Tuple& args) {
  //"Return the rendered buffer as an RGB string";
  
  _VERBOSE("RendererAgg::tostring_argb");
  
  args.verify_length(0);
  int row_len = width*4;
  unsigned char* buf_tmp = new unsigned char[row_len * height];
  if (buf_tmp ==NULL) {
    //todo: also handle allocation throw
    throw Py::MemoryError("RendererAgg::tostring_argb could not allocate memory");
  }
  agg::rendering_buffer renderingBufferTmp;
  renderingBufferTmp.attach(buf_tmp,
			    width,
			    height,
			    row_len);
  
  agg::color_conv(&renderingBufferTmp, renderingBuffer, agg::color_conv_rgba32_to_argb32());
  
  
  //todo: how to do this with native CXX
  PyObject* o = Py_BuildValue("s#",
			      buf_tmp,
			      row_len * height);
  delete [] buf_tmp;
  return Py::asObject(o);
}

Py::Object
RendererAgg::tostring_bgra(const Py::Tuple& args) {
  //"Return the rendered buffer as an RGB string";
  
  _VERBOSE("RendererAgg::tostring_bgra");
  
  args.verify_length(0);
  int row_len = width*4;
  unsigned char* buf_tmp = new unsigned char[row_len * height];
  if (buf_tmp ==NULL) {
    //todo: also handle allocation throw
    throw Py::MemoryError("RendererAgg::tostring_bgra could not allocate memory");
  }
  agg::rendering_buffer renderingBufferTmp;
  renderingBufferTmp.attach(buf_tmp,
			    width,
			    height,
			    row_len);
  
  agg::color_conv(&renderingBufferTmp, renderingBuffer, agg::color_conv_rgba32_to_bgra32());
  
  
  //todo: how to do this with native CXX
  PyObject* o = Py_BuildValue("s#",
			      buf_tmp,
			      row_len * height);
  delete [] buf_tmp;
  return Py::asObject(o);
}

Py::Object
RendererAgg::buffer_rgba(const Py::Tuple& args) {
  //"expose the rendered buffer as Python buffer object, starting from postion x,y";
  
  _VERBOSE("RendererAgg::buffer_rgba");
  
  args.verify_length(2);
  int startw = Py::Int(args[0]);
  int starth = Py::Int(args[1]);
  int row_len = width*4;
  int start=row_len*starth+startw*4;
  return Py::asObject(PyBuffer_FromMemory( pixBuffer+start, row_len*height-start));
}



Py::Object
RendererAgg::clear(const Py::Tuple& args) {
  //"clear the rendered buffer";
  
  _VERBOSE("RendererAgg::clear");
  
  args.verify_length(0);
  rendererBase->clear(agg::rgba(1, 1, 1, 0));
  
  return Py::Object();
}


agg::rgba
RendererAgg::rgb_to_color(const Py::SeqBase<Py::Object>& rgb, double alpha) {
  _VERBOSE("RendererAgg::rgb_to_color");
  
  double r = Py::Float(rgb[0]);
  double g = Py::Float(rgb[1]);
  double b = Py::Float(rgb[2]);
  return agg::rgba(r, g, b, alpha);
  
}


double
RendererAgg::points_to_pixels_snapto(const Py::Object& points) {
  // convert a value in points to pixels depending on renderer dpi and
  // screen pixels per inch
  // snap return pixels to grid
  _VERBOSE("RendererAgg::points_to_pixels_snapto");
  double p = Py::Float( points ) ;
  //return (int)(p*PIXELS_PER_INCH/72.0*dpi/72.0)+0.5;
  return (int)(p*dpi/72.0)+0.5;
  
  
}

double
RendererAgg::points_to_pixels( const Py::Object& points) {
  _VERBOSE("RendererAgg::points_to_pixels");
  double p = Py::Float( points ) ;
  //return p * PIXELS_PER_INCH/72.0*dpi/72.0;
  return p * dpi/72.0;
}


RendererAgg::~RendererAgg() {
  
  _VERBOSE("RendererAgg::~RendererAgg");
  
  
  delete slineP8;
  delete slineBin;
  delete theRasterizer;
  delete rendererAA;
  delete rendererBin;
  delete rendererBase;
  delete pixFmt;
  delete renderingBuffer;
  
  delete alphaMask;
  delete alphaMaskRenderingBuffer;
  delete [] alphaBuffer;
  delete [] pixBuffer;
  delete pixfmtAlphaMask;
  delete rendererBaseAlphaMask;
  delete rendererAlphaMask;
  delete scanlineAlphaMask;
  
}

/* ------------ module methods ------------- */
Py::Object _backend_agg_module::new_renderer (const Py::Tuple &args,
					      const Py::Dict &kws)
{
  
  if (args.length() != 3 )
    {
      throw Py::RuntimeError("Incorrect # of args to RendererAgg(width, height, dpi).");
    }
  
  int debug;
  if ( kws.hasKey("debug") ) debug = Py::Int( kws["debug"] );
  else debug=0;
  
  int width = Py::Int(args[0]);
  int height = Py::Int(args[1]);
  double dpi = Py::Float(args[2]);
  return Py::asObject(new RendererAgg(width, height, dpi, debug));
}


void BufferRegion::init_type() {
  behaviors().name("BufferRegion");
  behaviors().doc("A wrapper to pass agg buffer objects to and from the python level");
  
  add_varargs_method("to_string", &BufferRegion::to_string,
		     "to_string()");
  
}


void RendererAgg::init_type()
{
  behaviors().name("RendererAgg");
  behaviors().doc("The agg backend extension module");
  
  add_varargs_method("draw_path", &RendererAgg::draw_path,
		     "draw_path(gc, rgbFace, native_path, transform)\n");
  add_varargs_method("convert_to_native_path", &RendererAgg::convert_to_native_path,
		     "convert_to_native_path(vertices, codes)\n");
  add_varargs_method("draw_markers", &RendererAgg::draw_markers,
		     "draw_markers(gc, marker_path, marker_trans, vertices, codes, rgbFace)\n");
  add_varargs_method("draw_text_image", &RendererAgg::draw_text_image,
		     "draw_text_image(font_image, x, y, r, g, b, a)\n");
  add_varargs_method("draw_image", &RendererAgg::draw_image,
		     "draw_image(x, y, im)");
  add_varargs_method("write_rgba", &RendererAgg::write_rgba,
		     "write_rgba(fname)");
  add_varargs_method("write_png", &RendererAgg::write_png,
		     "write_png(fname)");
  add_varargs_method("tostring_rgb", &RendererAgg::tostring_rgb,
		     "s = tostring_rgb()");
  add_varargs_method("tostring_argb", &RendererAgg::tostring_argb,
		     "s = tostring_argb()");
  add_varargs_method("tostring_bgra", &RendererAgg::tostring_bgra,
		     "s = tostring_bgra()");
  add_varargs_method("buffer_rgba", &RendererAgg::buffer_rgba,
		     "buffer = buffer_rgba()");
  add_varargs_method("clear", &RendererAgg::clear,
		     "clear()");
  add_varargs_method("copy_from_bbox", &RendererAgg::copy_from_bbox,
		     "copy_from_bbox(bbox)");
  
  add_varargs_method("restore_region", &RendererAgg::restore_region,
		     "restore_region(region)");
}

void PathAgg::init_type()
{
  behaviors().name("PathAgg");
  behaviors().doc("A native Agg path object");
}

extern "C"
DL_EXPORT(void)
  init_backend_agg(void)
{
  //static _backend_agg_module* _backend_agg = new _backend_agg_module;
  
  _VERBOSE("init_backend_agg");
  
  import_array();
  
  static _backend_agg_module* _backend_agg = NULL;
  _backend_agg = new _backend_agg_module;
  
};

import {GET_INFOBOX_DONE, GET_COUNTRIES_DONE, DRAG_END_POLYGON, DRAG_END_POLYGON_FAIL, GIVE_UP} from '../actions';


function moveTo(paths, src, latLng) {
    let polygon = new google.maps.Polygon();
    polygon.setPaths(paths);
    paths = polygon.getPaths();
    let boundsCenter = src, // center of the polygonbounds
        newPoints = [], // array on which we'll store our new points
        newPaths = []; // array containing the new paths that make up the polygon

    // loop all the points of the original path and calculate the bearing + distance of that point relative to the center of the shape
    for (var p = 0; p < paths.getLength(); p++) {
        let path = paths.getAt(p);
        newPoints.push([]);

        for (var i = 0; i < path.getLength(); i++) {
            newPoints[newPoints.length - 1].push({
                heading: google.maps.geometry.spherical.computeHeading(boundsCenter, path.getAt(i)),
                distance: google.maps.geometry.spherical.computeDistanceBetween(boundsCenter, path.getAt(i))
            });
        }
    }

    // now that we have the "relative" points, rebuild the shapes on the new location around the new center
    for (var j = 0, jl = newPoints.length; j < jl; j++) {
        var shapeCoords = [],
            relativePoint = newPoints[j];
        for (var k = 0, kl = relativePoint.length; k < kl; k++) {
            shapeCoords.push(google.maps.geometry.spherical.computeOffset(
                latLng,
                relativePoint[k].distance,
                relativePoint[k].heading
            ));
        }
        newPaths.push(shapeCoords);
    }
    return newPaths;
}

function decodePaths(paths) {
    let result = [];
    for (var i = 0; i < paths.length; i++) {
        result.push(google.maps.geometry.encoding.decodePath(paths[i]));
    }
    return result;
}


function extractPolygons(countries) {
    return countries.map(country => {
        let originalPath = decodePaths(country.polygon);
        return {
            id: country.id,
            draggable: true,
            isSolved: false,
            infobox: {},
            paths: moveTo(
                originalPath,
                new google.maps.LatLng(country.center[1], country.center[0]),
                new google.maps.LatLng(country.default_position[0], country.default_position[1])),
            originalPath: originalPath,
            answer: new google.maps.LatLngBounds(
                new google.maps.LatLng(country.answer[0][1], country.answer[0][0]),
                new google.maps.LatLng(country.answer[1][1], country.answer[1][0])),
        }
    });
}


const polygons = (state = [], action) => {
    switch (action.type) {
        case GET_INFOBOX_DONE:
            return state.map((country) => {
                if (country.id === action.id) {
                    return {...country, infobox: action.data};
                }
                return country
            });
        case GET_COUNTRIES_DONE:
            return extractPolygons(action.countries);
        case GIVE_UP:
            return state.map((polygon) => {
                    if (!polygon.isSolved) {
                        return {...polygon,
                            draggable: false,
                            paths: polygon.originalPath,
                        };
                    }
                    return polygon
                });
        case DRAG_END_POLYGON_FAIL:
            return state.map((polygon) => {
                    if (polygon.id === action.id) {
                        return {...polygon, paths: action.paths};
                    }
                    return polygon
                });
        case DRAG_END_POLYGON:
            return state.map((polygon) => {
                    if (polygon.id === action.id) {
                        return {...polygon,
                            draggable: false,
                            isSolved: true,
                            paths: polygon.originalPath,
                        };
                    }
                    return polygon
                });
        default:
            return state
    }
};


export default polygons
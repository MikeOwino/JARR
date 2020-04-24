import qs from "qs";
import { createSlice } from "@reduxjs/toolkit";
import { apiUrl } from "../../const";
import { doRetryOnTokenExpiration } from "../login/userSlice";

const clusterSlice = createSlice({
  name: "cluster",
  initialState: { filters: { },
                  loading: false,
                  clusters: [],
                  requestedClusterId: null,
                  loadedCluster: {},
  },
  reducers: {
    requestedClustersList(state, action) {
      const filters = { ...state.filters };
      if (action.payload.filters.feedId
          || action.payload.filters.categoryId === "all") {
        delete filters["category_id"];
      }
      if (action.payload.filters.feedId) {
        filters["feed_id"] = action.payload.filters.feedId;

      } else if (action.payload.filters.categoryId) {
        if (action.payload.filters.categoryId !== "all" ) {
          filters["category_id"] = action.payload.filters.categoryId;
        }
        if (filters["feed_id"]) {
          delete filters["feed_id"];
        }
      }
      if (action.payload.filters.filter) {
        filters.filter = action.payload.filters.filter;
      } else if (action.payload.filters.filter === null) {
        delete filters.filter;
      }
      return { ...state, filters, loading: true, clusters: [] };
    },
    retrievedClustersList(state, action) {
      return { ...state, loading: false,
               clusters: action.payload.clusters };
    },
    requestedCluster(state, action) {
      return { ...state,
               requestedClusterId: action.payload.clusterId,
               loadedCluster: {},
      };
    },
    retrievedCluster(state, action) {
      return { ...state,
               // marking retrived cluster as read
               clusters: state.clusters.map((cluster) => {
                 if(cluster.id === action.payload.cluster.id) {
                    return { ...cluster, read: true };
                 }
                 return cluster;
               }),
               loadedCluster: action.payload.cluster,
      };
    },
    updateClusterAttrs(state, action) {
      const alterCluster = (cluster) => {
        if (cluster.id === action.payload.clusterId) {
          return { ...cluster,
                   read: action.payload.read === undefined ? cluster.read : action.payload.read,
                   liked: action.payload.liked === undefined ? cluster.liked : action.payload.liked };
          }
          return cluster;
      };
      return { ...state,
               // marking updated cluster as unread
               clusters: state.clusters.map(alterCluster),
      };
    },
    removeClusterSelection(state, action) {
      return { ...state, loadedCluster: {}, requestedClusterId: null };
    },
    markedAllAsRead(state, action) {
      return { ...state, clusters: [] };
    },
  },
});

export const { requestedClustersList, retrievedClustersList,
               requestedCluster, retrievedCluster,
               updateClusterAttrs,
               removeClusterSelection,
               markedAllAsRead,
} = clusterSlice.actions;
export default clusterSlice.reducer;

export const doListClusters = (filters): AppThunk => async (dispatch, getState) => {
  dispatch(requestedClustersList({ filters }));
  const params = qs.stringify(getState().clusters.filters);
  const result = await doRetryOnTokenExpiration({
    method: "get",
    url: apiUrl + "/clusters?" + params,
  }, dispatch, getState);
  dispatch(retrievedClustersList({ clusters: result.data }));
};

export const doFetchCluster = (clusterId): AppThunk => async (dispatch, getState) => {
  dispatch(requestedCluster({ clusterId }));
  const result = await doRetryOnTokenExpiration({
    method: "get",
    url: apiUrl + "/cluster/" + clusterId,
  }, dispatch, getState);
  dispatch(retrievedCluster({ cluster: result.data }));
};

export const doEditCluster = (clusterId, payload): AppThunk => async (dispatch, getState) => {
  dispatch(updateClusterAttrs({ clusterId, ...payload }));
  await doRetryOnTokenExpiration({
    method: "put",
    url: apiUrl + "/cluster/" + clusterId,
    data: payload,
  }, dispatch, getState);
};

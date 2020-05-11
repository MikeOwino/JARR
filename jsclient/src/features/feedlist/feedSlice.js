import qs from "qs";
import { createSlice } from "@reduxjs/toolkit";
import { doRetryOnTokenExpiration } from "../../authSlice";
import { apiUrl } from "../../const";
import { storageGet, storageSet } from "../../storageUtils";

const triboolMapping = {"true": true, "false": false, "null": null};


function mergeCategoriesWithUnreads(feedListRows, unreads,
                                    isParentFolded) {
  const categories = [];
  return feedListRows.map((row) => {
    const unread = unreads[`${row.type}-${row.id}`];
    let index;
    if(row.type === "categ" || row.type === "all-categ") {
      index = categories.length * 3;
      categories.push(row.id);
    } else if (unread) {
      index = categories.indexOf(row["category_id"]) * 3 + 1 / unread;
    } else {
      index = categories.indexOf(row["category_id"]) * 3 + 2;
    }
    return { ...row, unread: unread ? unread : null, index,
             folded: row.folded === undefined ? isParentFolded: row.folded };
  }).sort((row1, row2) => (row1.index - row2.index));
}

const defaultFilter = (row) => ( // will display row if
  !row.folded  // row is not folded
  || row.type === "categ" // row is a category (can't be folded)
  || row.type === "all-categ" // row is the "all categ" category (idem)
  // row is a feed without category (idem)
  || (row.type === "feed" && row["category_id"] === null)
);
const feedSlice = createSlice({
  name: "feeds",
  initialState: { loadingFeeds: true,
                  loadingUnreadCounts: true,
                  feedListRows: [],
                  unreads: {},
                  isParentFolded: storageGet("left-menu-folded") === "true",
                  isOpen: triboolMapping[storageGet("left-menu-open")],
                  feedListFilter: defaultFilter,
                  icons: {},
                  categoryAsFeed: {},
  },
  reducers: {
    requestedFeeds(state, action) {
      return { ...state, loadingFeeds: true };
    },
    requestedUnreadCounts(state, action) {
      return { ...state, loadingUnreadCounts: true };
    },
    setSearchFilter(state, action) {
      if (!action.payload) {
        return { ...state, feedListFilter: defaultFilter, };
      }
      const feedSearchStr = action.payload.toLowerCase();
      return { ...state,
               feedListFilter: (row) => (
                 row.type !== "categ" && row.type !== "all-categ"
                 && row.str.toLowerCase().includes(feedSearchStr)
               ),
      };
    },
    toggleAllFolding(state, action) {
      const newFolding = !state.isParentFolded;
      storageSet("left-menu-folded", newFolding);
      return { ...state,
               feedListRows: state.feedListRows.map((row) => {
                 return { ...row, folded: newFolding, };
               }),
               isParentFolded: newFolding };
    },
    toggleFolding(state, action) {
      return { ...state, feedListRows: state.feedListRows.map((row) => {
          return { ...row, folded: action.payload === row["category_id"] || (row["type"] === "categ" && row.id === action.payload) ? !row.folded : row.folded };
      })};
    },
    loadedFeeds(state, action) {
      const categoryAsFeed = {};
      const icons = {};
      action.payload.feedListRows.forEach((row) => {
        if(row.type === "feed" && row["icon_url"]) {
          icons[row.id] = row["icon_url"];
          categoryAsFeed[row.id] = row["category_id"];
        }
      });
      return { ...state, icons, categoryAsFeed, loadingFeeds: false,
               feedListRows: mergeCategoriesWithUnreads(action.payload.feedListRows,
                                                        state.unreads,
                                                        state.isParentFolded),
      };
    },
    loadedUnreadCounts(state, action) {
      return { ...state, loadedUnreadCounts: false,
               unreads: action.payload.unreads,
               feedListRows: mergeCategoriesWithUnreads(state.feedListRows,
                                                        action.payload.unreads,
                                                        state.isParentFolded),
      };
    },
    toggleMenu(state, action) {
      storageSet("left-menu-open", action.payload);
      return { ...state, isOpen: action.payload };
    },
    createdObj(state, action) {
      const feedListRow = { unread: 0, id: action.payload.data.id };
      if(action.payload.type === "category") {
        feedListRow.str = action.payload.data.name;
        feedListRow.type = "categ";
      } else {
        feedListRow.str = action.payload.data.title;
        feedListRow["category_id"] = action.payload.data["category_id"];
        feedListRow.type = "feed";
      }
      return { ...state,
               feedListRows: mergeCategoriesWithUnreads(
                   [ ...state.feedListRows, feedListRow ],
                   state.unreads, state.isParentFolded),
      };
    },
    changeReadCount(state, action) {
      const unreads = { ...state.unreads };
      const readChange = action.payload.action === "unread" ? 1 : -1;
      action.payload.feedsId.forEach((feedId) => {
        unreads[`feed-${feedId}`] += readChange;
        unreads[`categ-${state.categoryAsFeed[feedId]}`] += readChange;
      });
      return { ...state, unreads,
               feedListRows: mergeCategoriesWithUnreads(state.feedListRows,
                                                        unreads,
                                                        state.isParentFolded),
      };
    },
    editedObj(state, action) {
      const updated = {};
      const updatedState = {};
      if (action.payload.data.name) {  // category
        updated.str = action.payload.data.name;
      } else if (action.payload.data["category_id"]) {
        updated["category_id"] = action.payload.data["category_id"];
        updatedState.categoryAsFeed = {
          ...state.categoryAsFeed,
          [action.payload.id]: action.payload.data["category_id"]}
        ;
      } else if (action.payload.data.title) {
        updated.str = action.payload.data.title;
      } else { // nor name or title have been edited, nothing to change
        return state;
      }
      return { ...state,
               feedListRows: mergeCategoriesWithUnreads(
                 state.feedListRows.map((row) => {
                    if (((action.payload.objType === "feed" && row.type === "feed")
                       || (action.payload.objType === "category" && row.type === "categ"))
                       && action.payload.id === row.id) {
                      return { ...row, ...updated };
                    }
                    return row;
                  }), state.unreads, state.isParentFolded),
      };
    },
    deletedObj(state, action) {
      const type = action.payload.objType === "category" ? "categ" : "feed";
      return { ...state,
               feedListRows: state.feedListRows.filter((row) => (
                 row.type !== type || row.id !== action.payload.id)),
              };
    },
  },
});

export const { requestedFeeds, loadedFeeds,
               requestedUnreadCounts, loadedUnreadCounts,
               toggleMenu, toggleAllFolding, toggleFolding,
               createdObj, setSearchFilter,
               changeReadCount,
               editedObj, deletedObj,
} = feedSlice.actions;
export default feedSlice.reducer;

export const doFetchFeeds = (): AppThunk => async (dispatch, getState) => {
  dispatch(requestedFeeds());
  const result = await doRetryOnTokenExpiration({
    method: "get",
    url: `${apiUrl}/list-feeds`,
  }, dispatch, getState);
  dispatch(loadedFeeds({ feedListRows: result.data }));
};

export const doFetchUnreadCount = (): AppThunk => async (dispatch, getState) => {
  dispatch(requestedUnreadCounts());
  const result = await doRetryOnTokenExpiration({
    method: "get",
    url: `${apiUrl}/unreads`,
  }, dispatch, getState);
  dispatch(loadedUnreadCounts({ unreads: result.data }));
};

export const doCreateObj = (type): AppThunk => async (dispatch, getState) => {
  const result = await doRetryOnTokenExpiration({
    method: "post",
    url: `${apiUrl}/${type}`,
    data: getState().edit.loadedObj,
  }, dispatch, getState);
  dispatch(createdObj({ data: result.data, type }));
};

export const doEditObj = (objType): AppThunk => async (dispatch, getState) => {
  const editState = getState().edit;
  const data = {};
  editState.editedKeys.forEach((key) => {
    data[key] = editState.loadedObj[key];
  });
  if (objType !== "user") {
    dispatch(editedObj({ id: editState.loadedObj.id, objType, data }));
  }
  await doRetryOnTokenExpiration({
    method: "put",
    url: `${apiUrl}/${objType}${editState.loadedObj.id ? `/${editState.loadedObj.id}` : ""}`,
    data,
  }, dispatch, getState);
};

export const doDeleteObj = (id, objType): AppThunk => async (dispatch, getState) => {
  await doRetryOnTokenExpiration({
    method: "delete",
    url: `${apiUrl}/${objType}${id ? `/${id}` : ""}`,
  }, dispatch, getState);
  dispatch(deletedObj({ id, objType }));
};

export const doMarkAllAsRead = (onlySingles): AppThunk => async (dispatch, getState) => {
  const params = { ...getState().clusters.filters };
  if(onlySingles) {
      params["only_singles"] = true;
  }
  // dispatch(requestedMarkAllAsRead({ onlySingles })); // useless for now
  const stringifiedParams = qs.stringify(params);
  const result = await doRetryOnTokenExpiration({
    method: "put",
    url: `${apiUrl}/mark-all-as-read?${stringifiedParams}`,
  }, dispatch, getState);
  dispatch(loadedUnreadCounts({ unreads: result.data }));
};

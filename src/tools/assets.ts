import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebflowClient } from "webflow-api";
import { z } from "zod";
import { requestOptions } from "../mcp";
import { formatErrorResponse, formatResponse } from "../utils";

export function registerAssetsTools(
  server: McpServer,
  getClient: () => WebflowClient
) {
  // GET https://api.webflow.com/v2/sites/:site_id/assets
  server.tool(
    "assets_list",
    "List all assets uploaded to a site. Returns asset details including file information, URLs, and metadata.",
    {
      site_id: z.string().describe("Unique identifier for the Site."),
    },
    async ({ site_id }) => {
      try {
        const response = await getClient().assets.list(site_id, requestOptions);
        return formatResponse(response);
      } catch (error) {
        return formatErrorResponse(error);
      }
    }
  );

  // POST https://api.webflow.com/v2/sites/:site_id/assets
  server.tool(
    "assets_create",
    "Create a new asset by uploading a file to a site. Returns upload details and asset metadata.",
    {
      site_id: z.string().describe("Unique identifier for the Site."),
      fileName: z.string().describe("File name including file extension. File names must be less than 100 characters."),
      fileHash: z.string().describe("MD5 hash of the file"),
      displayName: z.string().optional().describe("Display name for the asset."),
      parentFolder: z.string().optional().describe("Parent folder ID for organizing the asset."),
    },
    async ({ site_id, fileName, fileHash, displayName, parentFolder }) => {
      try {
        const requestBody: any = {
          fileName,
          fileHash
        };
        if (displayName) requestBody.displayName = displayName;
        if (parentFolder) requestBody.parentFolder = parentFolder;

        const response = await getClient().assets.create(
          site_id,
          requestBody,
          requestOptions
        );
        return formatResponse(response);
      } catch (error) {
        return formatErrorResponse(error);
      }
    }
  );

  // GET https://api.webflow.com/v2/assets/:asset_id
  server.tool(
    "assets_get",
    "Get detailed information about a specific asset including its metadata, variants, and URLs.",
    {
      asset_id: z.string().describe("Unique identifier for the Asset."),
    },
    async ({ asset_id }) => {
      try {
        const response = await getClient().assets.get(asset_id, requestOptions);
        return formatResponse(response);
      } catch (error) {
        return formatErrorResponse(error);
      }
    }
  );

  // GET https://api.webflow.com/v2/sites/:site_id/asset_folders
  server.tool(
    "asset_folders_list",
    "List all asset folders within a site. Returns folder hierarchy and organization structure.",
    {
      site_id: z.string().describe("Unique identifier for the Site."),
    },
    async ({ site_id }) => {
      try {
        const response = await getClient().assets.listFolders(
          site_id,
          requestOptions
        );
        return formatResponse(response);
      } catch (error) {
        return formatErrorResponse(error);
      }
    }
  );

  // POST https://api.webflow.com/v2/sites/:site_id/asset_folders
  server.tool(
    "asset_folders_create",
    "Create a new asset folder within a site for organizing assets.",
    {
      site_id: z.string().describe("Unique identifier for the Site."),
      displayName: z.string().describe("A human readable name for the Asset Folder."),
      parentFolder: z.string().optional().describe("An optional pointer to a parent Asset Folder (or null for root)."),
    },
    async ({ site_id, displayName, parentFolder }) => {
      try {
        const requestBody: any = { displayName };
        if (parentFolder) requestBody.parentFolder = parentFolder;

        const response = await getClient().assets.createFolder(
          site_id,
          requestBody,
          requestOptions
        );
        return formatResponse(response);
      } catch (error) {
        return formatErrorResponse(error);
      }
    }
  );

  // GET https://api.webflow.com/v2/asset_folders/:asset_folder_id
  server.tool(
    "asset_folders_get",
    "Get detailed information about a specific asset folder including its contents and hierarchy.",
    {
      asset_folder_id: z.string().describe("Unique identifier for the Asset Folder."),
    },
    async ({ asset_folder_id }) => {
      try {
        const response = await getClient().assets.getFolder(
          asset_folder_id,
          requestOptions
        );
        return formatResponse(response);
      } catch (error) {
        return formatErrorResponse(error);
      }
    }
  );
}